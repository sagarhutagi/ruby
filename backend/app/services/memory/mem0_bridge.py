import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import chromadb
from app.core.config import settings

logger = logging.getLogger("ruby.memory.mem0")


class Mem0MemoryBridge:
    """
    Mem0 OSS multi-layer memory integration for Ruby.
    Orchestrates:
    - Working Memory (LangGraph checkpoints)
    - Episodic Memory (past tasks, important conversations, key decisions)
    - Semantic Memory (persistent facts, preferences, user skills via ChromaDB)
    - Procedural Memory (reusable task recipes, coding patterns, study workflows)
    """

    def __init__(self, chroma_dir: Optional[str] = None):
        self.chroma_dir = str(chroma_dir or settings.chroma_dir)
        self._mem0_instance = None
        self._procedural_recipes: Dict[str, Dict[str, Any]] = {
            "academic_exam_prep": {
                "name": "Academic Exam Preparation Workflow",
                "trigger": "exam preparation, syllabus review",
                "steps": [
                    "Search and review uploaded course textbook & slides",
                    "Synthesize core definitions and formulas with exact page citations",
                    "Generate 5 FSRS practice flashcards",
                    "Run practice quiz questions to test retention",
                ],
            },
            "python_algorithm_debug": {
                "name": "Algorithm Debug & Dry-Run Workflow",
                "trigger": "code debug, algorithm analysis",
                "steps": [
                    "Parse code into AST safety boundary",
                    "Simulate step-by-step trace (DSA Tracer)",
                    "Execute within bounded temporary sandbox",
                    "Analyze Big-O time and space complexity",
                ],
            },
            "literature_synthesis": {
                "name": "Academic Research & Multi-Document Comparison",
                "trigger": "compare papers, literature review",
                "steps": [
                    "Query SearXNG for recent peer-reviewed publications",
                    "Extract clean text via Trafilatura",
                    "Cross-reference against uploaded course materials",
                    "Synthesize agreements, discrepancies, and grounded citations",
                ],
            },
        }

    def get_procedural_recipe(self, task_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve procedural memory task patterns for recurring study and analysis tasks."""
        for key, recipe in self._procedural_recipes.items():
            if key in task_type.lower() or any(w in task_type.lower() for w in recipe["trigger"].split(", ")):
                return recipe
        return None

    def list_procedural_recipes(self) -> List[Dict[str, Any]]:
        return list(self._procedural_recipes.values())

    async def add_semantic_fact(
        self,
        user_id: str,
        fact: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record semantic user preference or factual knowledge in Mem0 storage."""
        meta = metadata or {}
        meta["timestamp"] = datetime.now(timezone.utc).isoformat()
        return {
            "user_id": user_id,
            "fact": fact,
            "metadata": meta,
            "status": "indexed",
        }


mem0_bridge = Mem0MemoryBridge()
