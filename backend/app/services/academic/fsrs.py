import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple


class FSRSAlgorithm:
    """
    Free Spaced Repetition Scheduler (FSRS) implementation.
    Calculates card stability, difficulty, retrievability, and optimal review intervals.
    """

    # Initial stability by rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    INIT_STABILITY = {1: 0.4, 2: 0.8, 3: 2.4, 4: 5.8}
    INIT_DIFFICULTY = {1: 7.5, 2: 6.0, 3: 5.0, 4: 3.5}

    @classmethod
    def calculate_retrievability(cls, elapsed_days: int, stability: float) -> float:
        """Power-law forgetting curve: R(t, S) = (1 + t / (9 * S))^-1."""
        if stability <= 0:
            return 0.0
        return round(math.pow(1.0 + (elapsed_days / (9.0 * stability)), -1.0), 4)

    @classmethod
    def schedule_review(
        cls,
        rating: int,  # 1=Again, 2=Hard, 3=Good, 4=Easy
        state: int = 0,  # 0=New, 1=Learning, 2=Review, 3=Relearning
        current_difficulty: float = 5.0,
        current_stability: float = 1.0,
        reps: int = 0,
        lapses: int = 0,
        elapsed_days: int = 0,
    ) -> Dict[str, Any]:
        rating = max(1, min(4, rating))

        # First review (New card)
        if state == 0:
            new_stability = cls.INIT_STABILITY.get(rating, 2.4)
            new_difficulty = cls.INIT_DIFFICULTY.get(rating, 5.0)
            new_state = 1 if rating == 1 else 2
            new_reps = 1
            new_lapses = 1 if rating == 1 else 0
        else:
            # Update Difficulty
            # Mean reversion towards initial difficulty
            diff_delta = -0.7 * (rating - 3)
            new_difficulty = max(1.0, min(10.0, current_difficulty + diff_delta))

            # Update Stability
            retrievability = cls.calculate_retrievability(elapsed_days, current_stability)
            if rating == 1:
                # Lapse / Failed recall
                new_stability = max(0.2, current_stability * 0.25)
                new_state = 3  # Relearning
                new_lapses = lapses + 1
            else:
                # Successful recall
                hard_penalty = 0.8 if rating == 2 else 1.0
                easy_bonus = 1.3 if rating == 4 else 1.0
                growth_factor = 1.0 + math.exp(2.5 - new_difficulty * 0.15) * math.pow(current_stability, -0.2) * (1.0 - retrievability) * hard_penalty * easy_bonus
                new_stability = max(current_stability + 0.1, current_stability * growth_factor)
                new_state = 2  # Review
                new_lapses = lapses

            new_reps = reps + 1

        # Calculate optimal interval for 90% target retention
        # I = 9 * S * (1/0.90 - 1) = S
        interval_days = max(1, int(round(new_stability * 1.0)))

        # Next due date
        now = datetime.now(timezone.utc)
        due_date = (now + timedelta(days=interval_days)).strftime("%Y-%m-%d")

        return {
            "state": new_state,
            "difficulty": round(new_difficulty, 2),
            "stability": round(new_stability, 2),
            "reps": new_reps,
            "lapses": new_lapses,
            "scheduled_days": interval_days,
            "elapsed_days": 0,
            "due_date": due_date,
            "retrievability": 1.0,
        }


fsrs = FSRSAlgorithm()
