import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import deque
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_
from app.models.entities import KnowledgeNode, KnowledgeEdge, Document, DocumentChunk, Subject

logger = logging.getLogger("ruby.services.graph")


class KnowledgeGraphService:
    """Manages concepts, relational edges, prerequisite topologies, and auto-extraction."""

    async def get_graph(
        self,
        session: AsyncSession,
        subject_id: Optional[str] = None,
        node_type: Optional[str] = None,
        verified_only: bool = False,
    ) -> Dict[str, Any]:
        """Fetch filtered graph nodes and edges for visualization and inspection."""
        # Query nodes
        node_stmt = select(KnowledgeNode)
        filters = []
        if subject_id:
            filters.append(KnowledgeNode.subject_id == subject_id)
        if node_type:
            filters.append(KnowledgeNode.node_type == node_type)
        if verified_only:
            filters.append(KnowledgeNode.is_verified == True)  # noqa: E712

        if filters:
            node_stmt = node_stmt.where(and_(*filters))

        nodes = (await session.execute(node_stmt)).scalars().all()
        node_ids = {n.id for n in nodes}

        # Query edges connecting existing nodes
        if not node_ids:
            return {"nodes": [], "edges": []}

        edge_stmt = select(KnowledgeEdge).where(
            and_(
                KnowledgeEdge.source_id.in_(node_ids),
                KnowledgeEdge.target_id.in_(node_ids),
            )
        )
        if verified_only:
            edge_stmt = edge_stmt.where(KnowledgeEdge.is_verified == True)  # noqa: E712

        edges = (await session.execute(edge_stmt)).scalars().all()

        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "node_type": n.node_type,
                    "description": n.description,
                    "subject_id": n.subject_id,
                    "document_id": n.document_id,
                    "position_x": n.position_x,
                    "position_y": n.position_y,
                    "is_verified": n.is_verified,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relationship_type": e.relationship_type,
                    "is_verified": e.is_verified,
                }
                for e in edges
            ],
        }

    async def create_node(
        self,
        session: AsyncSession,
        label: str,
        node_type: str = "concept",
        description: Optional[str] = None,
        subject_id: Optional[str] = None,
        document_id: Optional[str] = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
        is_verified: bool = True,
    ) -> KnowledgeNode:
        """Create a knowledge node with deduplication by label within subject."""
        # Check duplicate
        stmt = select(KnowledgeNode).where(
            KnowledgeNode.label.ilike(label.strip())
        )
        if subject_id:
            stmt = stmt.where(KnowledgeNode.subject_id == subject_id)

        existing = await session.scalar(stmt)
        if existing:
            # Update existing node description if none was set
            if not existing.description and description:
                existing.description = description
                await session.commit()
            return existing

        node = KnowledgeNode(
            label=label.strip(),
            node_type=node_type,
            description=description,
            subject_id=subject_id,
            document_id=document_id,
            position_x=position_x,
            position_y=position_y,
            is_verified=is_verified,
        )
        session.add(node)
        await session.commit()
        await session.refresh(node)
        return node

    async def update_node(
        self,
        session: AsyncSession,
        node_id: str,
        label: Optional[str] = None,
        node_type: Optional[str] = None,
        description: Optional[str] = None,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
        is_verified: Optional[bool] = None,
    ) -> Optional[KnowledgeNode]:
        """Update properties of an existing knowledge node."""
        node = await session.scalar(select(KnowledgeNode).where(KnowledgeNode.id == node_id))
        if not node:
            return None

        if label is not None:
            node.label = label.strip()
        if node_type is not None:
            node.node_type = node_type
        if description is not None:
            node.description = description
        if position_x is not None:
            node.position_x = position_x
        if position_y is not None:
            node.position_y = position_y
        if is_verified is not None:
            node.is_verified = is_verified

        await session.commit()
        await session.refresh(node)
        return node

    async def delete_node(self, session: AsyncSession, node_id: str) -> bool:
        """Delete a node and its attached edges."""
        node = await session.scalar(select(KnowledgeNode).where(KnowledgeNode.id == node_id))
        if not node:
            return False

        # Delete edges connected to this node
        await session.execute(
            delete(KnowledgeEdge).where(
                or_(KnowledgeEdge.source_id == node_id, KnowledgeEdge.target_id == node_id)
            )
        )
        await session.delete(node)
        await session.commit()
        return True

    async def create_edge(
        self,
        session: AsyncSession,
        source_id: str,
        target_id: str,
        relationship_type: str = "RELATED_TO",
        is_verified: bool = True,
    ) -> Optional[KnowledgeEdge]:
        """Create a directed relation edge between two nodes."""
        if source_id == target_id:
            return None

        # Verify nodes exist
        src = await session.scalar(select(KnowledgeNode).where(KnowledgeNode.id == source_id))
        tgt = await session.scalar(select(KnowledgeNode).where(KnowledgeNode.id == target_id))
        if not src or not tgt:
            return None

        # Check existing edge
        stmt = select(KnowledgeEdge).where(
            and_(
                KnowledgeEdge.source_id == source_id,
                KnowledgeEdge.target_id == target_id,
                KnowledgeEdge.relationship_type == relationship_type,
            )
        )
        existing = await session.scalar(stmt)
        if existing:
            return existing

        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            is_verified=is_verified,
        )
        session.add(edge)
        await session.commit()
        await session.refresh(edge)
        return edge

    async def delete_edge(self, session: AsyncSession, edge_id: str) -> bool:
        """Delete a knowledge edge."""
        edge = await session.scalar(select(KnowledgeEdge).where(KnowledgeEdge.id == edge_id))
        if not edge:
            return False
        await session.delete(edge)
        await session.commit()
        return True

    async def get_prerequisite_chain(self, session: AsyncSession, target_node_id: str) -> Dict[str, Any]:
        """
        Compute the topological prerequisite chain leading to a target node.
        Edge: source -- PREREQUISITE_OF --> target implies source must be learned before target.
        """
        target = await session.scalar(select(KnowledgeNode).where(KnowledgeNode.id == target_node_id))
        if not target:
            return {"error": "Target node not found", "chain": []}

        # BFS / DFS traversal backwards along PREREQUISITE_OF edges
        visited: Set[str] = set()
        queue: deque = deque([target_node_id])
        chain_nodes: List[Dict[str, Any]] = []

        while queue:
            curr_id = queue.popleft()
            if curr_id in visited:
                continue
            visited.add(curr_id)

            curr_node = await session.scalar(select(KnowledgeNode).where(KnowledgeNode.id == curr_id))
            if curr_node and curr_id != target_node_id:
                chain_nodes.append({
                    "id": curr_node.id,
                    "label": curr_node.label,
                    "node_type": curr_node.node_type,
                    "description": curr_node.description,
                })

            # Find prerequisites of curr_id (i.e. edges where target_id == curr_id and rel == PREREQUISITE_OF)
            prereq_edges = (
                await session.execute(
                    select(KnowledgeEdge).where(
                        and_(
                            KnowledgeEdge.target_id == curr_id,
                            KnowledgeEdge.relationship_type == "PREREQUISITE_OF",
                        )
                    )
                )
            ).scalars().all()

            for pe in prereq_edges:
                if pe.source_id not in visited:
                    queue.append(pe.source_id)

        # Reverse so earliest prerequisites come first
        chain_nodes.reverse()

        return {
            "target": {
                "id": target.id,
                "label": target.label,
                "node_type": target.node_type,
                "description": target.description,
            },
            "prerequisites_count": len(chain_nodes),
            "study_order": chain_nodes,
        }

    async def extract_concepts_from_document(
        self,
        session: AsyncSession,
        document_id: str,
        auto_link: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract academic concepts, formulas, and topic relationships from document chunks.
        Marked as `is_verified=False` for distinctive UI treatment as unverified AI suggestions.
        """
        doc = await session.scalar(select(Document).where(Document.id == document_id))
        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        # Get chunks
        chunks = (
            await session.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index.asc())
            )
        ).scalars().all()

        if not chunks:
            return {"nodes_created": 0, "edges_created": 0, "concepts": []}

        # Parent Document Node
        doc_node = await self.create_node(
            session=session,
            label=doc.title,
            node_type="document",
            description=f"Source document: {doc.filename}",
            subject_id=doc.subject_id,
            document_id=doc.id,
            is_verified=True,
        )

        created_nodes: List[KnowledgeNode] = []
        created_edges: List[KnowledgeEdge] = []
        seen_labels: Set[str] = {doc.title.lower()}

        # Heading and definition regexes
        definition_pattern = re.compile(
            r"([A-Z][a-zA-Z0-9\s-]{2,40})\s+(?:is defined as|refers to|is an? (?:algorithm|protocol|data structure|concept|technique))\s+([^.\n]+)",
            re.IGNORECASE,
        )
        bold_concept_pattern = re.compile(r"\*\*([A-Za-z0-9\s-]{3,35})\*\*")
        formula_pattern = re.compile(r"\$\$([^\$]+)\$\$|\$([^\$]+)\$")

        x_offset = 100.0
        y_offset = 100.0

        for chunk in chunks:
            # 1. Section Headings -> topic / concept node
            if chunk.section_heading:
                clean_heading = chunk.section_heading.strip("# \t\r\n")
                if clean_heading and clean_heading.lower() not in seen_labels and len(clean_heading) <= 60:
                    seen_labels.add(clean_heading.lower())
                    topic_node = await self.create_node(
                        session=session,
                        label=clean_heading,
                        node_type="topic",
                        description=f"Section in {doc.title}",
                        subject_id=doc.subject_id,
                        document_id=doc.id,
                        position_x=x_offset,
                        position_y=y_offset,
                        is_verified=False,
                    )
                    created_nodes.append(topic_node)
                    x_offset += 160.0
                    if x_offset > 800:
                        x_offset = 100.0
                        y_offset += 140.0

                    if auto_link:
                        edge = await self.create_edge(
                            session=session,
                            source_id=topic_node.id,
                            target_id=doc_node.id,
                            relationship_type="PART_OF",
                            is_verified=False,
                        )
                        if edge:
                            created_edges.append(edge)

            # 2. Extract defined concepts
            for match in definition_pattern.finditer(chunk.content):
                term = match.group(1).strip()
                meaning = match.group(2).strip()
                if term.lower() not in seen_labels and len(term) >= 3 and len(term) <= 50:
                    seen_labels.add(term.lower())
                    c_node = await self.create_node(
                        session=session,
                        label=term,
                        node_type="concept",
                        description=meaning[:250],
                        subject_id=doc.subject_id,
                        document_id=doc.id,
                        position_x=x_offset,
                        position_y=y_offset,
                        is_verified=False,
                    )
                    created_nodes.append(c_node)
                    x_offset += 160.0
                    if x_offset > 800:
                        x_offset = 100.0
                        y_offset += 140.0

                    if auto_link:
                        edge = await self.create_edge(
                            session=session,
                            source_id=c_node.id,
                            target_id=doc_node.id,
                            relationship_type="EXPLAINED_IN",
                            is_verified=False,
                        )
                        if edge:
                            created_edges.append(edge)

            # 3. Extract bold academic terms
            for match in bold_concept_pattern.finditer(chunk.content):
                term = match.group(1).strip()
                if term.lower() not in seen_labels and len(term) >= 3 and len(term) <= 40:
                    seen_labels.add(term.lower())
                    b_node = await self.create_node(
                        session=session,
                        label=term,
                        node_type="concept",
                        description=f"Key term extracted from {doc.title}",
                        subject_id=doc.subject_id,
                        document_id=doc.id,
                        position_x=x_offset,
                        position_y=y_offset,
                        is_verified=False,
                    )
                    created_nodes.append(b_node)
                    x_offset += 160.0
                    if x_offset > 800:
                        x_offset = 100.0
                        y_offset += 140.0

            # 4. Extract mathematical formulas
            for match in formula_pattern.finditer(chunk.content):
                form_text = (match.group(1) or match.group(2) or "").strip()
                if form_text and len(form_text) <= 50 and form_text.lower() not in seen_labels:
                    seen_labels.add(form_text.lower())
                    f_node = await self.create_node(
                        session=session,
                        label=f"${form_text}$",
                        node_type="formula",
                        description=f"Formula from {doc.title}",
                        subject_id=doc.subject_id,
                        document_id=doc.id,
                        position_x=x_offset,
                        position_y=y_offset,
                        is_verified=False,
                    )
                    created_nodes.append(f_node)
                    x_offset += 160.0
                    if x_offset > 800:
                        x_offset = 100.0
                        y_offset += 140.0

        return {
            "document_id": doc.id,
            "document_title": doc.title,
            "nodes_created": len(created_nodes),
            "edges_created": len(created_edges),
            "concepts": [n.label for n in created_nodes[:20]],
        }


knowledge_graph_service = KnowledgeGraphService()
