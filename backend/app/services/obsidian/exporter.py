import os
import io
import re
import zipfile
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import KnowledgeNode, KnowledgeEdge, Subject

logger = logging.getLogger("ruby.services.obsidian")


class ObsidianVaultExporter:
    """Exports Knowledge Graph nodes and edges to Obsidian-compatible Markdown vaults with wikilinks."""

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Sanitize node label into a clean filesystem filename."""
        cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
        cleaned = cleaned.replace("$", "").strip()
        return cleaned[:80] or "Untitled_Note"

    async def generate_vault_notes(
        self,
        session: AsyncSession,
        subject_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate in-memory representation of Obsidian notes with YAML frontmatter and [[wikilinks]].
        """
        # Fetch subjects mapping
        subjects_stmt = select(Subject)
        subjects = (await session.execute(subjects_stmt)).scalars().all()
        subj_map = {s.id: s.name for s in subjects}

        # Fetch nodes
        node_stmt = select(KnowledgeNode)
        if subject_id:
            node_stmt = node_stmt.where(KnowledgeNode.subject_id == subject_id)
        nodes = (await session.execute(node_stmt)).scalars().all()

        if not nodes:
            return []

        node_ids = {n.id for n in nodes}
        node_by_id = {n.id: n for n in nodes}

        # Fetch edges between nodes
        edge_stmt = select(KnowledgeEdge).where(
            KnowledgeEdge.source_id.in_(node_ids) | KnowledgeEdge.target_id.in_(node_ids)
        )
        edges = (await session.execute(edge_stmt)).scalars().all()

        # Build adjacency mapping
        out_edges: Dict[str, List[KnowledgeEdge]] = {n.id: [] for n in nodes}
        in_edges: Dict[str, List[KnowledgeEdge]] = {n.id: [] for n in nodes}
        for e in edges:
            if e.source_id in out_edges:
                out_edges[e.source_id].append(e)
            if e.target_id in in_edges:
                in_edges[e.target_id].append(e)

        notes: List[Dict[str, Any]] = []

        for node in nodes:
            subj_name = subj_map.get(node.subject_id or "", "General")
            clean_name = self.sanitize_filename(node.label)
            created_str = node.created_at.strftime("%Y-%m-%d") if node.created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # YAML Frontmatter
            frontmatter = [
                "---",
                f'id: "{node.id}"',
                f'title: "{node.label.replace(chr(34), "")}"',
                f'type: "{node.node_type}"',
                f'subject: "{subj_name}"',
                f'verified: {str(node.is_verified).lower()}',
                f'created: "{created_str}"',
                "tags:",
                "  - academic",
                "  - ruby",
                f"  - {self.sanitize_filename(subj_name).lower()}",
                f"  - {node.node_type.lower()}",
                "---",
                "",
            ]

            # Content
            content_lines = [
                f"# {node.label}",
                "",
                f"> [!INFO] **Type:** `{node.node_type}` | **Subject:** `{subj_name}`" + (" | *AI Suggested (Unverified)*" if not node.is_verified else ""),
                "",
            ]

            if node.description:
                content_lines.extend([
                    "## Overview",
                    node.description,
                    "",
                ])

            # Connected [[wikilinks]]
            connected_sections: List[str] = []

            # Prerequisites (Incoming PREREQUISITE_OF edges)
            prereqs = [e for e in in_edges[node.id] if e.relationship_type == "PREREQUISITE_OF"]
            if prereqs:
                connected_sections.append("### Prerequisites")
                for e in prereqs:
                    src_node = node_by_id.get(e.source_id)
                    if src_node:
                        connected_sections.append(f"- [[{self.sanitize_filename(src_node.label)}]]")

            # Outgoing links
            outgoing = out_edges[node.id]
            if outgoing:
                related = [e for e in outgoing if e.relationship_type != "PREREQUISITE_OF"]
                leads_to = [e for e in outgoing if e.relationship_type == "PREREQUISITE_OF"]

                if leads_to:
                    connected_sections.append("### Enables (Prerequisite For)")
                    for e in leads_to:
                        tgt_node = node_by_id.get(e.target_id)
                        if tgt_node:
                            connected_sections.append(f"- [[{self.sanitize_filename(tgt_node.label)}]]")

                if related:
                    connected_sections.append("### Related Concepts")
                    for e in related:
                        tgt_node = node_by_id.get(e.target_id)
                        if tgt_node:
                            connected_sections.append(f"- `{e.relationship_type}` ➔ [[{self.sanitize_filename(tgt_node.label)}]]")

            if connected_sections:
                content_lines.extend(["## Knowledge Graph Connections", *connected_sections, ""])

            note_markdown = "\n".join(frontmatter + content_lines)
            folder_name = self.sanitize_filename(subj_name)
            filename = f"{clean_name}.md"
            rel_path = os.path.join(folder_name, filename)

            notes.append({
                "id": node.id,
                "label": node.label,
                "folder": folder_name,
                "filename": filename,
                "relative_path": rel_path,
                "content": note_markdown,
            })

        # Add Master Index Note (_RUBY_INDEX.md)
        index_lines = [
            "---",
            'title: "RUBY Academic Knowledge Index"',
            'type: "index"',
            "tags:",
            "  - ruby-index",
            "  - academic",
            "---",
            "",
            "# RUBY Academic Knowledge Index",
            "",
            f"*Generated by RUBY on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
            f"**Total Indexed Concepts:** {len(nodes)}",
            "",
            "## Concepts by Subject",
            "",
        ]

        # Group by subject
        by_subj: Dict[str, List[Dict[str, Any]]] = {}
        for note in notes:
            by_subj.setdefault(note["folder"], []).append(note)

        for subj, subj_notes in sorted(by_subj.items()):
            index_lines.append(f"### {subj} ({len(subj_notes)})")
            for sn in sorted(subj_notes, key=lambda x: x["label"].lower()):
                clean_target = self.sanitize_filename(sn["label"])
                index_lines.append(f"- [[{clean_target}]]")
            index_lines.append("")

        notes.append({
            "id": "_ruby_index",
            "label": "Master Index",
            "folder": "",
            "filename": "_RUBY_INDEX.md",
            "relative_path": "_RUBY_INDEX.md",
            "content": "\n".join(index_lines),
        })

        return notes

    async def preview_export(
        self,
        session: AsyncSession,
        vault_path: str,
        subject_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check destination directory and return preview of files to create and potential conflicts.
        """
        notes = await self.generate_vault_notes(session, subject_id)
        to_create: List[str] = []
        to_overwrite: List[str] = []

        vault_abs = os.path.abspath(vault_path)

        for note in notes:
            dest_file = os.path.join(vault_abs, note["relative_path"])
            if os.path.exists(dest_file):
                to_overwrite.append(note["relative_path"])
            else:
                to_create.append(note["relative_path"])

        return {
            "vault_path": vault_abs,
            "total_notes": len(notes),
            "files_to_create": to_create,
            "files_to_overwrite": to_overwrite,
            "has_conflicts": len(to_overwrite) > 0,
        }

    async def export_to_vault(
        self,
        session: AsyncSession,
        vault_path: str,
        subject_id: Optional[str] = None,
        allow_overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Write notes to local Obsidian vault filesystem path with overwrite protection.
        """
        notes = await self.generate_vault_notes(session, subject_id)
        vault_abs = os.path.abspath(vault_path)
        os.makedirs(vault_abs, exist_ok=True)

        written: List[str] = []
        skipped: List[str] = []

        for note in notes:
            dest_file = os.path.join(vault_abs, note["relative_path"])
            file_dir = os.path.dirname(dest_file)
            if file_dir:
                os.makedirs(file_dir, exist_ok=True)

            if os.path.exists(dest_file) and not allow_overwrite:
                skipped.append(note["relative_path"])
                continue

            with open(dest_file, "w", encoding="utf-8") as f:
                f.write(note["content"])
            written.append(note["relative_path"])

        return {
            "vault_path": vault_abs,
            "written_count": len(written),
            "skipped_count": len(skipped),
            "written_files": written,
            "skipped_files": skipped,
        }

    async def create_vault_zip(
        self,
        session: AsyncSession,
        subject_id: Optional[str] = None,
    ) -> io.BytesIO:
        """
        Package all generated markdown notes into an in-memory ZIP archive for browser download.
        """
        notes = await self.generate_vault_notes(session, subject_id)
        buf = io.BytesIO()

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for note in notes:
                zf.writestr(note["relative_path"], note["content"].encode("utf-8"))

        buf.seek(0)
        return buf


obsidian_exporter = ObsidianVaultExporter()
