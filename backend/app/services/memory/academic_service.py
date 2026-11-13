from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AcademicRecord

logger = logging.getLogger("ruby.memory.academic")


class AcademicMemoryService:
    """
    Dedicated Canonical Structured Academic Memory Layer for Ruby.
    Stores and manages verified student academic performance (marks, exams, assessments,
    attendance, CGPA) in SQLite relational storage.
    Enforces atomic multi-score ingestion, deduplication, zero-score distinction,
    and structured querying (averages, rankings, trends, comparisons).
    """

    @classmethod
    async def create_or_update_record(
        cls,
        session: AsyncSession,
        user_id: str = "default_user",
        term: str = "Current",
        subject_code: Optional[str] = None,
        subject_name: Optional[str] = None,
        assessment_type: str = "assessment",
        marks_obtained: Optional[float] = None,
        max_marks: Optional[float] = None,
        percentage: Optional[float] = None,
        result_status: str = "available",
        assessment_date: Optional[str] = None,
        institution: Optional[str] = None,
        grade: Optional[str] = None,
        weight: float = 1.0,
        notes: Optional[str] = None,
        source: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
        record_type: str = "assessment",
    ) -> AcademicRecord:
        """
        Creates a new academic record or updates an existing one matching
        (user_id, subject_code, term, assessment_type).
        """
        clean_code = subject_code.strip().upper() if subject_code else None
        clean_term = term.strip()
        clean_type = assessment_type.strip()

        # Compute percentage if marks and max marks are available
        calc_pct = percentage
        if marks_obtained is not None and max_marks and max_marks > 0:
            calc_pct = round((marks_obtained / max_marks) * 100.0, 2)

        # Result status validation
        status = result_status.lower()
        if status not in ("available", "pending", "absent", "not_applicable"):
            status = "available" if marks_obtained is not None else "pending"

        # Check existing record
        stmt = select(AcademicRecord).where(
            AcademicRecord.user_id == user_id,
            AcademicRecord.subject_code == clean_code,
            AcademicRecord.term == clean_term,
            AcademicRecord.assessment_type == clean_type,
        )
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()

        if record:
            # Update existing record in-place (deduplication & correction)
            logger.info("Updating existing AcademicRecord: %s - %s (%s)", clean_code, clean_type, clean_term)
            if subject_name:
                record.subject_name = subject_name
            if institution:
                record.institution = institution
            record.marks_obtained = marks_obtained
            record.max_marks = max_marks
            record.percentage = calc_pct
            record.result_status = status
            if assessment_date:
                record.assessment_date = assessment_date
            if grade:
                record.grade = grade
            record.weight = weight
            if notes:
                record.notes = notes
            if source:
                record.source = source
            if provenance:
                record.provenance = provenance
            record.record_type = record_type
        else:
            # Insert new record
            logger.info("Inserting new AcademicRecord: %s - %s (%s)", clean_code, clean_type, clean_term)
            record = AcademicRecord(
                user_id=user_id,
                institution=institution,
                term=clean_term,
                subject_code=clean_code,
                subject_name=subject_name,
                assessment_type=clean_type,
                marks_obtained=marks_obtained,
                max_marks=max_marks,
                percentage=calc_pct,
                result_status=status,
                assessment_date=assessment_date,
                weight=weight,
                grade=grade,
                notes=notes,
                source=source,
                provenance=provenance,
                record_type=record_type,
            )
            session.add(record)

        await session.commit()
        await session.refresh(record)
        return record

    @classmethod
    async def parse_and_ingest_scorecard(
        cls,
        session: AsyncSession,
        text: str,
        user_id: str = "default_user",
        term: str = "Current",
        institution: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[AcademicRecord]:
        """
        Parses multi-subject scorecards, test results, and grade lists.
        Extracts structured records atomically without producing isolated numerical memories.
        """
        records: List[AcademicRecord] = []

        # 1. Subject code + Name + Assessment + Marks (e.g., "CS301 Computer Networks ISA 1: 44/50")
        score_patterns = [
            # Pattern A: CS301 Computer Networks ISA 1: 44/50 or 44 / 50
            r"(?P<code>[A-Z]{2,4}\d{2,4}[A-Z0-9]*)\s+(?P<name>[A-Za-z\s]+?)\s+(?P<type>ISA\s*\d+|ESA|Midterm|Final|Quiz\s*\d+|Assignment\s*\d+|Practical|Lab)\s*:\s*(?P<score>\d+(?:\.\d+)?)\s*\/\s*(?P<max>\d+(?:\.\d+)?)",
            # Pattern B: Computer Networks (CS301) - ISA 1: 44/50
            r"(?P<name>[A-Za-z\s]+?)\s*\((?P<code>[A-Z]{2,4}\d{2,4}[A-Z0-9]*)\)\s*[-:]?\s*(?P<type>ISA\s*\d+|ESA|Midterm|Final|Quiz\s*\d+|Assignment\s*\d+|Practical|Lab)\s*:\s*(?P<score>\d+(?:\.\d+)?)\s*\/\s*(?P<max>\d+(?:\.\d+)?)",
            # Pattern C: CS301 ISA 1: 44/50
            r"(?P<code>[A-Z]{2,4}\d{2,4}[A-Z0-9]*)\s+(?P<type>ISA\s*\d+|ESA|Midterm|Final|Quiz\s*\d+|Assignment\s*\d+|Practical|Lab)\s*:\s*(?P<score>\d+(?:\.\d+)?)\s*\/\s*(?P<max>\d+(?:\.\d+)?)",
            # Pattern D: Pending result (e.g., "CS301 Computer Networks ISA 2: Pending")
            r"(?P<code>[A-Z]{2,4}\d{2,4}[A-Z0-9]*)\s*(?P<name>[A-Za-z\s]+?)?\s+(?P<type>ISA\s*\d+|ESA|Midterm|Final|Quiz\s*\d+|Assignment\s*\d+|Practical|Lab)\s*:\s*(?P<status>Pending|Awaited|Absent)",
        ]

        lines = text.splitlines()
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            matched = False
            for pat in score_patterns:
                m = re.search(pat, line_str, flags=re.IGNORECASE)
                if m:
                    gd = m.groupdict()
                    code = gd.get("code")
                    name = gd.get("name", "").strip() if gd.get("name") else None
                    a_type = gd.get("type", "assessment").strip()

                    status_str = gd.get("status")
                    if status_str:
                        status = "pending" if status_str.lower() in ("pending", "awaited") else "absent"
                        rec = await cls.create_or_update_record(
                            session=session,
                            user_id=user_id,
                            term=term,
                            subject_code=code,
                            subject_name=name,
                            assessment_type=a_type,
                            marks_obtained=None,
                            max_marks=None,
                            result_status=status,
                            institution=institution,
                            source=source or "scorecard_import",
                        )
                        records.append(rec)
                        matched = True
                        break

                    score = float(gd.get("score")) if gd.get("score") else None
                    max_score = float(gd.get("max")) if gd.get("max") else None

                    rec = await cls.create_or_update_record(
                        session=session,
                        user_id=user_id,
                        term=term,
                        subject_code=code,
                        subject_name=name,
                        assessment_type=a_type,
                        marks_obtained=score,
                        max_marks=max_score,
                        result_status="available",
                        institution=institution,
                        source=source or "scorecard_import",
                    )
                    records.append(rec)
                    matched = True
                    break

            # Check CGPA / SGPA
            if not matched:
                cgpa_match = re.search(r"(?:CGPA|SGPA|GPA)\s*[:=]\s*(\d+(?:\.\d+)?)", line_str, flags=re.IGNORECASE)
                if cgpa_match:
                    gpa_val = float(cgpa_match.group(1))
                    gpa_type = "cgpa" if "cgpa" in line_str.lower() else "sgpa"
                    rec = await cls.create_or_update_record(
                        session=session,
                        user_id=user_id,
                        term=term,
                        subject_code=gpa_type.upper(),
                        subject_name=f"Overall {gpa_type.upper()}",
                        assessment_type="Overall",
                        marks_obtained=gpa_val,
                        max_marks=10.0,
                        percentage=round((gpa_val / 10.0) * 100.0, 2),
                        result_status="available",
                        institution=institution,
                        source=source or "scorecard_import",
                        record_type=gpa_type,
                    )
                    records.append(rec)

        return records

    # ---------------------------------------------------------
    # Structured SQL Queries
    # ---------------------------------------------------------

    @classmethod
    async def get_marks_for_subject(
        cls,
        session: AsyncSession,
        subject_query: str,
        user_id: str = "default_user",
        term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves all assessment records for a subject by code or name."""
        stmt = select(AcademicRecord).where(
            AcademicRecord.user_id == user_id,
            or_(
                AcademicRecord.subject_code.ilike(f"%{subject_query}%"),
                AcademicRecord.subject_name.ilike(f"%{subject_query}%"),
            ),
        )
        if term:
            stmt = stmt.where(AcademicRecord.term == term)

        stmt = stmt.order_by(AcademicRecord.term.desc(), AcademicRecord.assessment_type)
        res = await session.execute(stmt)
        records = res.scalars().all()

        return [
            {
                "id": r.id,
                "term": r.term,
                "subject_code": r.subject_code,
                "subject_name": r.subject_name,
                "assessment_type": r.assessment_type,
                "marks_obtained": r.marks_obtained,
                "max_marks": r.max_marks,
                "percentage": r.percentage,
                "result_status": r.result_status,
                "grade": r.grade,
                "assessment_date": r.assessment_date,
            }
            for r in records
        ]

    @classmethod
    async def get_subject_percentage(
        cls,
        session: AsyncSession,
        subject_query: str,
        user_id: str = "default_user",
        term: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates cumulative and average percentage for a subject."""
        records = await cls.get_marks_for_subject(session, subject_query, user_id, term)
        available = [r for r in records if r["result_status"] == "available" and r["marks_obtained"] is not None and r["max_marks"]]

        if not available:
            return {
                "subject": subject_query,
                "term": term,
                "completed_assessments": 0,
                "cumulative_percentage": None,
                "total_marks_obtained": 0.0,
                "total_max_marks": 0.0,
            }

        total_obtained = sum(r["marks_obtained"] for r in available)
        total_max = sum(r["max_marks"] for r in available)
        cum_pct = round((total_obtained / total_max) * 100.0, 2) if total_max > 0 else 0.0

        return {
            "subject": available[0]["subject_name"] or available[0]["subject_code"] or subject_query,
            "subject_code": available[0]["subject_code"],
            "term": term or available[0]["term"],
            "completed_assessments": len(available),
            "cumulative_percentage": cum_pct,
            "total_marks_obtained": total_obtained,
            "total_max_marks": total_max,
            "breakdown": available,
        }

    @classmethod
    async def get_highest_lowest_scores(
        cls,
        session: AsyncSession,
        user_id: str = "default_user",
        term: Optional[str] = None,
        subject_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Finds highest and lowest scoring assessments by percentage."""
        stmt = select(AcademicRecord).where(
            AcademicRecord.user_id == user_id,
            AcademicRecord.result_status == "available",
            AcademicRecord.percentage.isnot(None),
        )
        if term:
            stmt = stmt.where(AcademicRecord.term == term)
        if subject_code:
            stmt = stmt.where(AcademicRecord.subject_code.ilike(f"%{subject_code}%"))

        res = await session.execute(stmt)
        records = res.scalars().all()

        if not records:
            return {"highest": None, "lowest": None, "count": 0}

        sorted_recs = sorted(records, key=lambda r: r.percentage or 0.0, reverse=True)
        high = sorted_recs[0]
        low = sorted_recs[-1]

        def fmt(r: AcademicRecord) -> Dict[str, Any]:
            return {
                "subject_code": r.subject_code,
                "subject_name": r.subject_name,
                "assessment_type": r.assessment_type,
                "term": r.term,
                "marks_obtained": r.marks_obtained,
                "max_marks": r.max_marks,
                "percentage": r.percentage,
            }

        return {
            "highest": fmt(high),
            "lowest": fmt(low),
            "count": len(sorted_recs),
        }

    @classmethod
    async def get_average_performance(
        cls,
        session: AsyncSession,
        user_id: str = "default_user",
        term: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates overall average score and percentage across all available subjects."""
        stmt = select(AcademicRecord).where(
            AcademicRecord.user_id == user_id,
            AcademicRecord.result_status == "available",
            AcademicRecord.percentage.isnot(None),
        )
        if term:
            stmt = stmt.where(AcademicRecord.term == term)

        res = await session.execute(stmt)
        records = res.scalars().all()

        if not records:
            return {"average_percentage": None, "total_assessments": 0, "term": term}

        total_pct = sum(r.percentage for r in records if r.percentage is not None)
        avg_pct = round(total_pct / len(records), 2)

        return {
            "average_percentage": avg_pct,
            "total_assessments": len(records),
            "term": term or "All Terms",
        }

    @classmethod
    async def compare_assessments(
        cls,
        session: AsyncSession,
        assessment_a: str = "ISA 1",
        assessment_b: str = "ISA 2",
        user_id: str = "default_user",
        term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Compares performance subject-by-subject between two assessment rounds."""
        stmt = select(AcademicRecord).where(
            AcademicRecord.user_id == user_id,
            or_(
                AcademicRecord.assessment_type.ilike(f"%{assessment_a}%"),
                AcademicRecord.assessment_type.ilike(f"%{assessment_b}%"),
            ),
        )
        if term:
            stmt = stmt.where(AcademicRecord.term == term)

        res = await session.execute(stmt)
        records = res.scalars().all()

        # Group by subject code
        by_subject: Dict[str, Dict[str, Any]] = {}
        for r in records:
            s_code = r.subject_code or r.subject_name or "UNKNOWN"
            if s_code not in by_subject:
                by_subject[s_code] = {
                    "subject_code": r.subject_code,
                    "subject_name": r.subject_name,
                    "assessment_a": None,
                    "assessment_b": None,
                }
            if assessment_a.lower() in r.assessment_type.lower():
                by_subject[s_code]["assessment_a"] = {
                    "type": r.assessment_type,
                    "marks": r.marks_obtained,
                    "max": r.max_marks,
                    "percentage": r.percentage,
                    "status": r.result_status,
                }
            elif assessment_b.lower() in r.assessment_type.lower():
                by_subject[s_code]["assessment_b"] = {
                    "type": r.assessment_type,
                    "marks": r.marks_obtained,
                    "max": r.max_marks,
                    "percentage": r.percentage,
                    "status": r.result_status,
                }

        comparisons = []
        for s_code, data in by_subject.items():
            pct_a = data["assessment_a"]["percentage"] if data["assessment_a"] else None
            pct_b = data["assessment_b"]["percentage"] if data["assessment_b"] else None
            delta = None
            if pct_a is not None and pct_b is not None:
                delta = round(pct_b - pct_a, 2)

            comparisons.append({
                "subject_code": data["subject_code"],
                "subject_name": data["subject_name"],
                "assessment_a": data["assessment_a"],
                "assessment_b": data["assessment_b"],
                "delta_percentage": delta,
                "improved": delta > 0 if delta is not None else None,
            })

        return comparisons

    @classmethod
    async def get_pending_results(
        cls,
        session: AsyncSession,
        user_id: str = "default_user",
        term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves all pending, awaited, or absent assessment records."""
        stmt = select(AcademicRecord).where(
            AcademicRecord.user_id == user_id,
            or_(
                AcademicRecord.result_status.in_(["pending", "absent"]),
                AcademicRecord.marks_obtained.is_(None),
            ),
        )
        if term:
            stmt = stmt.where(AcademicRecord.term == term)

        res = await session.execute(stmt)
        records = res.scalars().all()

        return [
            {
                "subject_code": r.subject_code,
                "subject_name": r.subject_name,
                "assessment_type": r.assessment_type,
                "term": r.term,
                "result_status": r.result_status,
                "assessment_date": r.assessment_date,
            }
            for r in records
        ]

    @classmethod
    async def get_performance_trends(
        cls,
        session: AsyncSession,
        user_id: str = "default_user",
    ) -> List[Dict[str, Any]]:
        """Aggregates chronological average percentages grouped by academic term."""
        stmt = select(
            AcademicRecord.term,
            func.avg(AcademicRecord.percentage).label("avg_pct"),
            func.count(AcademicRecord.id).label("count"),
        ).where(
            AcademicRecord.user_id == user_id,
            AcademicRecord.result_status == "available",
            AcademicRecord.percentage.isnot(None),
        ).group_by(AcademicRecord.term).order_by(AcademicRecord.created_at)

        res = await session.execute(stmt)
        rows = res.all()

        return [
            {
                "term": row.term,
                "average_percentage": round(row.avg_pct, 2) if row.avg_pct is not None else None,
                "assessments_count": row.count,
            }
            for row in rows
        ]


academic_memory_service = AcademicMemoryService()
