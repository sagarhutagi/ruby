from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import QuizSession, QuizQuestion, Subject

ACADEMIC_QUESTION_TEMPLATES = [
    # OS
    {
        "subject": "Operating Systems",
        "question_type": "mcq",
        "question_text": "Which of the following is NOT one of the four necessary Coffman conditions for deadlock?",
        "options": ["Mutual Exclusion", "Hold and Wait", "No Preemption", "Paging Segmentation"],
        "correct_answer": "Paging Segmentation",
        "explanation": "The 4 Coffman conditions are: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.",
    },
    {
        "subject": "Operating Systems",
        "question_type": "mcq",
        "question_text": "In Round Robin CPU scheduling, what happens if the time quantum is extremely large?",
        "options": ["Degenerates to FCFS", "Degenerates to SJF", "Throughput reaches 100%", "Causes thrashing"],
        "correct_answer": "Degenerates to FCFS",
        "explanation": "When the quantum is larger than the longest burst time, processes execute without interruption in order of arrival, identical to FCFS.",
    },
    # DSA
    {
        "subject": "Data Structures and Algorithms",
        "question_type": "mcq",
        "question_text": "What is the worst-case time complexity of searching for an element in an unbalanced Binary Search Tree?",
        "options": ["O(1)", "O(log n)", "O(n)", "O(n log n)"],
        "correct_answer": "O(n)",
        "explanation": "When an unbalanced BST becomes skewed (degenerate tree like a linked list), search degrades to O(n).",
    },
    {
        "subject": "Data Structures and Algorithms",
        "question_type": "true_false",
        "question_text": "Dijkstra's shortest path algorithm correctly finds the shortest path on graphs containing negative edge weights.",
        "options": ["True", "False"],
        "correct_answer": "False",
        "explanation": "Dijkstra's algorithm assumes edge weights are non-negative. For negative weights, the Bellman-Ford algorithm must be used.",
    },
    # CN
    {
        "subject": "Computer Networks",
        "question_type": "mcq",
        "question_text": "Which layer of the OSI model is responsible for reliable end-to-end communication and flow control?",
        "options": ["Network Layer", "Transport Layer", "Data Link Layer", "Session Layer"],
        "correct_answer": "Transport Layer",
        "explanation": "The Transport Layer (e.g. TCP) provides end-to-end communication, flow control, and error recovery.",
    },
    {
        "subject": "Computer Networks",
        "question_type": "mcq",
        "question_text": "How many usable host IP addresses are available in a /24 IPv4 subnet?",
        "options": ["256", "254", "255", "128"],
        "correct_answer": "254",
        "explanation": "A /24 subnet has 2^(32-24) = 256 total addresses. Subtracting 2 for Network ID and Broadcast IP yields 254 usable hosts.",
    },
    # DLCD
    {
        "subject": "Digital Logic and Computer Design",
        "question_type": "mcq",
        "question_text": "Which logic gate produces a HIGH (1) output only when an ODD number of inputs are HIGH (1)?",
        "options": ["AND Gate", "OR Gate", "XOR Gate", "NOR Gate"],
        "correct_answer": "XOR Gate",
        "explanation": "An Exclusive-OR (XOR) gate performs modulo-2 addition and outputs 1 when an odd number of inputs are 1.",
    },
    # Math
    {
        "subject": "Mathematics",
        "question_type": "mcq",
        "question_text": "What is the derivative of f(x) = ln(x) with respect to x?",
        "options": ["1/x", "e^x", "x", "1/(x^2)"],
        "correct_answer": "1/x",
        "explanation": "d/dx [ln(x)] = 1/x for x > 0.",
    },
]


class QuizEngine:
    @staticmethod
    async def create_quiz(
        session: AsyncSession,
        title: str,
        subject_id: Optional[str] = None,
        difficulty: str = "medium",
        question_count: int = 5,
        time_limit_minutes: int = 15,
    ) -> QuizSession:
        quiz = QuizSession(
            title=title,
            subject_id=subject_id,
            difficulty=difficulty,
            total_questions=0,
            correct_count=0,
            score_percentage=0.0,
            time_limit_minutes=time_limit_minutes,
            status="in_progress",
        )
        session.add(quiz)
        await session.flush()

        # Find subject name if provided
        subj_name = None
        if subject_id:
            subj = await session.scalar(select(Subject).where(Subject.id == subject_id))
            if subj:
                subj_name = subj.name

        # Select relevant templates
        candidates = [
            t for t in ACADEMIC_QUESTION_TEMPLATES
            if not subj_name or t["subject"].lower() in subj_name.lower() or subj_name.lower() in t["subject"].lower()
        ]
        if not candidates:
            candidates = ACADEMIC_QUESTION_TEMPLATES

        chosen = candidates[:question_count]
        for t in chosen:
            q = QuizQuestion(
                session_id=quiz.id,
                question_type=t["question_type"],
                question_text=t["question_text"],
                options=t["options"],
                correct_answer=t["correct_answer"],
                explanation=t["explanation"],
            )
            session.add(q)

        quiz.total_questions = len(chosen)
        await session.commit()
        await session.refresh(quiz)
        return quiz

    @staticmethod
    async def submit_quiz(
        session: AsyncSession,
        quiz_id: str,
        answers: Dict[str, str],
    ) -> Dict[str, Any]:
        quiz = await session.scalar(select(QuizSession).where(QuizSession.id == quiz_id))
        if not quiz:
            raise ValueError(f"Quiz session {quiz_id} not found.")

        q_stmt = select(QuizQuestion).where(QuizQuestion.session_id == quiz_id)
        questions = (await session.execute(q_stmt)).scalars().all()

        correct_count = 0
        mistakes = []

        for q in questions:
            user_ans = answers.get(q.id, "").strip()
            q.user_answer = user_ans
            is_correct = (user_ans.lower() == q.correct_answer.strip().lower())
            q.is_correct = is_correct

            if is_correct:
                correct_count += 1
            else:
                mistakes.append({
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "user_answer": user_ans or "(Unanswered)",
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                })

        score_pct = round((correct_count / max(1, len(questions))) * 100.0, 1)
        quiz.correct_count = correct_count
        quiz.score_percentage = score_pct
        quiz.status = "completed"
        await session.commit()

        return {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "status": "completed",
            "total_questions": len(questions),
            "correct_count": correct_count,
            "score_percentage": score_pct,
            "passed": (score_pct >= 60.0),
            "mistakes_review": mistakes,
        }


quiz_engine = QuizEngine()
