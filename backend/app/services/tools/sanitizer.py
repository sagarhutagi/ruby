import re
from typing import List, Optional


CONVERSATIONAL_PREFIXES = [
    r"^can you (please )?(explain|search for|look up|tell me about|find|give me info on)\b",
    r"^(please )?(explain|search for|look up|tell me about|find|show me)\b",
    r"^i want to (know|learn|understand|find out about)\b",
    r"^what (is|are|was|were)\b",
    r"^how (does|do|can|to)\b",
    r"^compare (the )?",
    r"^tell me (about )?",
    r"^find recent research papers about\b",
    r"^and compare them with my uploaded notes\b",
]

PUNCTUATION_STRIP_REGEX = re.compile(r"^[\s\"'`“”‘’\(\)\[\]\{\}\<\>\.,;:?!]+|[\s\"'`“”‘’\(\)\[\]\{\}\<\>\.,;:?!]+$")


class SearchQuerySanitizer:
    """
    Focused Search Query Sanitizer and Keyword Distiller.
    Prevents passing raw verbose prompt text to SearXNG.
    Enforces maximum keyword lengths, strips conversational filler,
    deduplicates queries, and supports multi-query decomposition.
    """

    @classmethod
    def sanitize_single_query(cls, raw_query: str, max_chars: int = 120, max_words: int = 12) -> Optional[str]:
        if not raw_query or not raw_query.strip():
            return None

        q = raw_query.strip()

        # Remove surrounding quotes, brackets, question marks
        q = PUNCTUATION_STRIP_REGEX.sub("", q).strip()

        # Remove common conversational prefixes iteratively
        lower_q = q.lower()
        for pat in CONVERSATIONAL_PREFIXES:
            m = re.match(pat, lower_q, flags=re.IGNORECASE)
            if m:
                q = q[m.end():].strip()
                lower_q = q.lower()

        # Strip punctuation again after prefix removal
        q = PUNCTUATION_STRIP_REGEX.sub("", q).strip()

        # Strip leading article "the " or "a " or "an "
        if q.lower().startswith("the "):
            q = q[4:].strip()
        elif q.lower().startswith("a "):
            q = q[2:].strip()
        elif q.lower().startswith("an "):
            q = q[3:].strip()

        # Remove any lingering "and tell me which architecture would be best..." or ", compare with my notes..." or prompt meta instructions
        q = re.split(r",?\s*(?:and\s+)?(?:compare\s+(?:them\s+)?with|tell\s+me\s+(?:which|what|how)|give\s+me|explain\s+how|and\s+tell|and\s+find)\b", q, flags=re.IGNORECASE)[0].strip()

        # Collapse whitespace
        q = " ".join(q.split())

        # If empty after cleaning, return None
        if not q or len(q) < 2:
            return None

        # Truncate to word/char limit
        words = q.split()
        if len(words) > max_words:
            q = " ".join(words[:max_words])

        if len(q) > max_chars:
            q = q[:max_chars].rsplit(" ", 1)[0]

        return q

    @classmethod
    def extract_queries_from_prompt(
        cls,
        prompt: str,
        max_queries: int = 3,
    ) -> List[str]:
        """
        Heuristic keyword distiller for prompts when tool calling arguments
        need fallback keyword extraction.
        """
        cleaned = cls.sanitize_single_query(prompt)
        if not cleaned:
            return []

        # Check for multi-clause queries separated by 'vs', 'versus', 'and', 'compared to'
        parts = re.split(r"\b(?:vs\.?|versus|compared to)\b", cleaned, flags=re.IGNORECASE)
        results: List[str] = []

        if len(parts) > 1 and len(parts) <= max_queries:
            for p in parts:
                sq = cls.sanitize_single_query(p)
                if sq and sq not in results:
                    results.append(sq)
            if results:
                return results

        return [cleaned]

    @classmethod
    def deduplicate_and_validate(cls, queries: List[str], max_queries: int = 3) -> List[str]:
        valid: List[str] = []
        seen = set()

        for q in queries:
            sanitized = cls.sanitize_single_query(q)
            if not sanitized:
                continue
            key = sanitized.lower()
            if key not in seen:
                seen.add(key)
                valid.append(sanitized)
            if len(valid) >= max_queries:
                break

        return valid


search_query_sanitizer = SearchQuerySanitizer()
