import time
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, delete
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
from app.models.entities import Memory, MemoryAuditEvent
from app.services.retrieval.embeddings import embedding_manager

logger = logging.getLogger("ruby.memory.service")


class MemoryService:
    """
    Academic 5-Tier Memory Subsystem.
    Types: working, episodic, semantic, profile, procedural.
    Supports candidate extraction, importance scoring, duplicate detection,
    contradiction flagging, consolidation, semantic retrieval, and full audit logging.
    """

    COLLECTION_NAME = "ruby_memories"

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = str((persist_dir or settings.chroma_dir).resolve() if isinstance(persist_dir or settings.chroma_dir, type(settings.chroma_dir)) else persist_dir or settings.chroma_dir)
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            if self._client is None:
                self._client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True),
                )
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def list_memories(
        self,
        session: AsyncSession,
        memory_type: Optional[str] = None,
        status: str = "active",
        is_pinned: Optional[bool] = None,
        q: Optional[str] = None,
    ) -> List[Memory]:
        stmt = select(Memory)
        if status:
            stmt = stmt.where(Memory.status == status)
        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type.lower())
        if is_pinned is not None:
            stmt = stmt.where(Memory.is_pinned == is_pinned)
        if q:
            stmt = stmt.where(Memory.content.ilike(f"%{q}%"))

        # Order pinned items first, then descending by importance, then by updated_at
        stmt = stmt.order_by(
            Memory.is_pinned.desc(),
            Memory.importance_score.desc(),
            Memory.updated_at.desc(),
        )
        return list((await session.execute(stmt)).scalars().all())

    async def create_memory(
        self,
        session: AsyncSession,
        content: str,
        memory_type: str = "semantic",
        importance_score: float = 0.5,
        confidence: float = 1.0,
        is_pinned: bool = False,
        source_conversation_id: Optional[str] = None,
        source_event: Optional[str] = None,
    ) -> Memory:
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Memory content cannot be empty.")

        mem = Memory(
            content=clean_content,
            memory_type=memory_type.lower(),
            importance_score=max(0.0, min(1.0, importance_score)),
            confidence=max(0.0, min(1.0, confidence)),
            is_pinned=is_pinned,
            status="active",
            source_conversation_id=source_conversation_id,
            source_event=source_event,
        )
        session.add(mem)
        await session.flush()

        # Index in ChromaDB for semantic memory retrieval
        try:
            coll = self._get_collection()
            provider = embedding_manager.get_provider()
            vec = await provider.embed_query(clean_content)
            coll.upsert(
                ids=[mem.id],
                documents=[clean_content],
                embeddings=[vec],
                metadatas=[{
                    "memory_id": mem.id,
                    "memory_type": mem.memory_type,
                    "importance": mem.importance_score,
                    "is_pinned": mem.is_pinned,
                }],
            )
        except Exception as e:
            logger.warning("Failed to index memory %s in Chroma: %s", mem.id, e)

        # Audit event
        audit = MemoryAuditEvent(
            memory_id=mem.id,
            action="created",
            details={
                "memory_type": mem.memory_type,
                "importance_score": mem.importance_score,
                "source_event": source_event,
            },
        )
        session.add(audit)
        await session.commit()
        await session.refresh(mem)
        return mem

    async def update_memory(
        self,
        session: AsyncSession,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        importance_score: Optional[float] = None,
        confidence: Optional[float] = None,
        is_pinned: Optional[bool] = None,
    ) -> Memory:
        mem = await session.scalar(select(Memory).where(Memory.id == memory_id))
        if not mem:
            raise ValueError(f"Memory {memory_id} not found.")

        changes: Dict[str, Any] = {}
        if content is not None and content.strip():
            changes["content"] = {"old": mem.content, "new": content.strip()}
            mem.content = content.strip()
        if memory_type is not None:
            changes["memory_type"] = {"old": mem.memory_type, "new": memory_type.lower()}
            mem.memory_type = memory_type.lower()
        if importance_score is not None:
            new_imp = max(0.0, min(1.0, importance_score))
            changes["importance_score"] = {"old": mem.importance_score, "new": new_imp}
            mem.importance_score = new_imp
        if confidence is not None:
            new_conf = max(0.0, min(1.0, confidence))
            changes["confidence"] = {"old": mem.confidence, "new": new_conf}
            mem.confidence = new_conf
        if is_pinned is not None:
            changes["is_pinned"] = {"old": mem.is_pinned, "new": is_pinned}
            mem.is_pinned = is_pinned

        # Update ChromaDB vector
        try:
            coll = self._get_collection()
            provider = embedding_manager.get_provider()
            vec = await provider.embed_query(mem.content)
            coll.upsert(
                ids=[mem.id],
                documents=[mem.content],
                embeddings=[vec],
                metadatas=[{
                    "memory_id": mem.id,
                    "memory_type": mem.memory_type,
                    "importance": mem.importance_score,
                    "is_pinned": mem.is_pinned,
                }],
            )
        except Exception as e:
            logger.warning("Failed to update memory %s in Chroma: %s", mem.id, e)

        # Audit event
        audit = MemoryAuditEvent(
            memory_id=mem.id,
            action="updated",
            details=changes,
        )
        session.add(audit)
        await session.commit()
        await session.refresh(mem)
        return mem

    async def delete_memory(
        self,
        session: AsyncSession,
        memory_id: str,
        hard_delete: bool = True,
    ) -> None:
        """
        Purges memory and completely removes all searchable representations and vector indexes.
        """
        mem = await session.scalar(select(Memory).where(Memory.id == memory_id))
        if not mem:
            return

        # 1. Purge from ChromaDB collection
        try:
            coll = self._get_collection()
            coll.delete(ids=[memory_id])
            logger.info("ChromaDB: Purged memory vector %s", memory_id)
        except Exception as e:
            logger.warning("Failed to delete memory %s from Chroma: %s", memory_id, e)

        # 2. Audit record
        audit = MemoryAuditEvent(
            memory_id=memory_id,
            action="deleted",
            details={"content_preview": mem.content[:60], "hard_delete": hard_delete},
        )
        session.add(audit)

        # 3. Database deletion or archive
        if hard_delete:
            await session.delete(mem)
        else:
            mem.status = "deleted"

        await session.commit()

    async def toggle_pin(self, session: AsyncSession, memory_id: str) -> Memory:
        mem = await session.scalar(select(Memory).where(Memory.id == memory_id))
        if not mem:
            raise ValueError(f"Memory {memory_id} not found.")

        mem.is_pinned = not mem.is_pinned
        audit = MemoryAuditEvent(
            memory_id=mem.id,
            action="pinned" if mem.is_pinned else "unpinned",
            details={"is_pinned": mem.is_pinned},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(mem)
        return mem

    async def search_memories(
        self,
        session: AsyncSession,
        query: str,
        memory_types: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Semantic search over memories with cosine distance ranking."""
        query = query.strip()
        if not query:
            return []

        coll = self._get_collection()
        if coll.count() == 0:
            return []

        provider = embedding_manager.get_provider()
        query_vec = await provider.embed_query(query)

        where_clause: Optional[Dict[str, Any]] = None
        if memory_types:
            if len(memory_types) == 1:
                where_clause = {"memory_type": memory_types[0].lower()}
            else:
                where_clause = {"memory_type": {"$in": [t.lower() for t in memory_types]}}

        try:
            results = coll.query(
                query_embeddings=[query_vec],
                n_results=min(top_k, coll.count()),
                where=where_clause,
            )
        except Exception as e:
            logger.warning("Chroma memory query error: %s", e)
            return []

        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results and results["distances"] else [0.0] * len(ids)

        if not ids:
            return []

        # Hydrate from SQLite
        stmt = select(Memory).where(Memory.id.in_(ids), Memory.status == "active")
        mems = {m.id: m for m in (await session.execute(stmt)).scalars().all()}

        output: List[Dict[str, Any]] = []
        for i, mid in enumerate(ids):
            if mid in mems:
                dist = float(distances[i]) if i < len(distances) else 1.0
                sim = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                output.append({
                    "memory": mems[mid],
                    "similarity": round(sim, 4),
                    "distance": round(dist, 4),
                })

        output.sort(key=lambda x: x["similarity"], reverse=True)
        return output

    async def get_context_memories(
        self,
        session: AsyncSession,
        query: str,
        top_k: int = 4,
    ) -> List[Memory]:
        """
        Retrieves authoritative memory context for conversation turns:
        1. All pinned active memories (user profile priorities).
        2. All active user profile and procedural preference memories.
        3. Semantically matching memories relevant to the query.
        Returns deduplicated memories ranked by pinned status and importance.
        """
        seen: Dict[str, Memory] = {}

        # 1. Pinned memories
        pinned_mems = await self.list_memories(session, status="active", is_pinned=True)
        for m in pinned_mems:
            seen[m.id] = m

        # 2. Profile and procedural preference memories (active)
        pref_mems = await self.list_memories(session, status="active", memory_type="profile")
        for m in pref_mems:
            seen[m.id] = m

        procedural_mems = await self.list_memories(session, status="active", memory_type="procedural")
        for m in procedural_mems:
            seen[m.id] = m

        # 3. Semantic search for query-relevant memories
        clean_q = query.strip()
        if clean_q:
            semantic_matches = await self.search_memories(session, query=clean_q, top_k=top_k)
            for sm in semantic_matches:
                if sm["similarity"] >= 0.45:
                    mem = sm["memory"]
                    seen[mem.id] = mem

        # Sort pinned first, then by importance descending, then updated_at descending
        return sorted(
            seen.values(),
            key=lambda x: (x.is_pinned, x.importance_score, x.updated_at),
            reverse=True,
        )

    async def extract_candidates(
        self,
        session: AsyncSession,
        text: str,
        conversation_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyses user text for memory extraction candidates:
        - Explicit Remember commands ("Please remember that...", "Keep in mind that...")
        - Preferences / Profile ("I prefer LaTeX", "My name is Mars", "My favorite language is Rust") -> Profile
        - Mistakes / Difficulties ("I don't understand paging", "I got confused on Dijkstra") -> Episodic
        - Facts / Definitions ("The formula for Bayes theorem is...") -> Semantic
        - Repeated instructions ("Always show Big-O complexity") -> Procedural
        Computes importance score, checks duplicates, and checks contradictions.
        """
        import re

        candidates: List[Dict[str, Any]] = []

        # Split text into candidate statements (by line and sentence boundaries)
        raw_statements: List[str] = []
        for block in text.split("\n"):
            block_clean = block.strip()
            if not block_clean:
                continue
            # If the block contains multiple punctuated sentences, check each sentence
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", block_clean) if len(s.strip()) > 8]
            if len(sentences) > 1:
                raw_statements.extend(sentences)
            else:
                raw_statements.append(block_clean)

        profile_triggers = [
            "i prefer", "i like", "i dislike", "i hate", "my goal is", "i am studying",
            "i am preparing for", "i want explanations in", "my name is", "call me",
            "my favorite", "my background is", "my major is", "my field is", "i live in",
            "i am an", "i am a", "as a student", "as an engineer"
        ]
        episodic_triggers = [
            "i struggled with", "i was confused by", "i made a mistake", "i keep forgetting",
            "i don't understand", "i failed to", "my weak area is", "i had difficulty with"
        ]
        procedural_triggers = [
            "always show", "always format", "preferred workflow", "never include",
            "always use", "never use", "do not use", "don't ever", "always include",
            "strictly follow", "respond in"
        ]
        semantic_triggers = [
            "is defined as", "formula for", "the theorem states", "key property of",
            "algorithm operates on", "complexity is"
        ]

        remember_pat = re.compile(
            r"^(?:please\s+)?(?:remember|keep in mind|note|don't forget)(?:\s+that)?:?\s*(.*)$",
            re.IGNORECASE,
        )

        existing_mems = await self.list_memories(session, status="active")

        for statement in raw_statements:
            statement_clean = statement.strip()
            if len(statement_clean) < 8:
                continue

            # Skip questions: user queries asking for information should not be formed into memories
            if statement_clean.endswith("?") or re.match(
                r"^(?:what|who|where|when|why|how|can you|could you|do you|tell me|is there|are there)\b",
                statement_clean,
                re.IGNORECASE,
            ):
                continue

            lower = statement_clean.lower()
            m_type = None
            imp = 0.5
            is_explicit_remember = False

            # Check explicit remember directive
            rem_match = remember_pat.match(statement_clean)
            extracted_statement = statement_clean
            if rem_match and rem_match.group(1).strip():
                extracted_statement = rem_match.group(1).strip()
                extracted_statement = extracted_statement[0].upper() + extracted_statement[1:]
                lower = extracted_statement.lower()
                is_explicit_remember = True
                imp = 0.9

            if any(t in lower for t in profile_triggers):
                m_type = "profile"
                imp = max(imp, 0.85 if is_explicit_remember else 0.8)
            elif any(t in lower for t in episodic_triggers):
                m_type = "episodic"
                imp = max(imp, 0.7)
            elif any(t in lower for t in procedural_triggers):
                m_type = "procedural"
                imp = max(imp, 0.85)
            elif any(t in lower for t in semantic_triggers):
                m_type = "semantic"
                imp = max(imp, 0.65)
            elif is_explicit_remember:
                m_type = "profile"
                imp = 0.85

            if m_type:
                # Duplicate check
                is_duplicate = False
                matched_id = None
                for ex in existing_mems:
                    if ex.content.lower() in lower or lower in ex.content.lower():
                        is_duplicate = True
                        matched_id = ex.id
                        break

                # Contradiction heuristic (e.g. "I prefer brief" vs "I prefer detailed")
                is_contradiction = False
                if m_type == "profile":
                    for ex in existing_mems:
                        if ex.memory_type == "profile":
                            if ("brief" in ex.content and "detailed" in lower) or ("detailed" in ex.content and "brief" in lower):
                                is_contradiction = True
                                break

                candidates.append({
                    "content": statement_clean,
                    "normalized_content": extracted_statement,
                    "memory_type": m_type,
                    "importance_score": imp,
                    "confidence": 0.95 if is_explicit_remember else 0.9,
                    "is_duplicate": is_duplicate,
                    "duplicate_memory_id": matched_id,
                    "is_contradiction": is_contradiction,
                    "source_conversation_id": conversation_id,
                    "is_explicit": is_explicit_remember,
                })

        return candidates

    async def get_audit_trail(
        self,
        session: AsyncSession,
        memory_id: Optional[str] = None,
    ) -> List[MemoryAuditEvent]:
        stmt = select(MemoryAuditEvent)
        if memory_id:
            stmt = stmt.where(MemoryAuditEvent.memory_id == memory_id)
        stmt = stmt.order_by(MemoryAuditEvent.created_at.desc()).limit(100)
        return list((await session.execute(stmt)).scalars().all())

    async def export_memories(self, session: AsyncSession) -> List[Dict[str, Any]]:
        mems = await self.list_memories(session, status="active")
        return [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "content": m.content,
                "importance_score": m.importance_score,
                "confidence": m.confidence,
                "is_pinned": m.is_pinned,
                "created_at": m.created_at.isoformat(),
            }
            for m in mems
        ]

    async def import_memories(self, session: AsyncSession, items: List[Dict[str, Any]]) -> int:
        count = 0
        for item in items:
            if "content" in item and item["content"].strip():
                await self.create_memory(
                    session=session,
                    content=item["content"],
                    memory_type=item.get("memory_type", "semantic"),
                    importance_score=float(item.get("importance_score", 0.5)),
                    confidence=float(item.get("confidence", 1.0)),
                    is_pinned=bool(item.get("is_pinned", False)),
                    source_event="import",
                )
                count += 1
        return count


memory_service = MemoryService()
