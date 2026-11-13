import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.session import get_db
from app.models.entities import FlashcardDeck, Flashcard, ReviewLog, QuizSession, QuizQuestion
from app.services.academic.math_engine import math_engine
from app.services.academic.sandbox import sandbox, dsa_tracer
from app.services.academic.simulators import (
    cpu_scheduler,
    bankers_simulator,
    page_simulator,
    subnet_calculator,
    circuit_simulator,
)
from app.services.academic.fsrs import fsrs
from app.services.academic.quiz_engine import quiz_engine

logger = logging.getLogger("ruby.api.academic")

router = APIRouter(prefix="/academic", tags=["academic"])


# --- MATH MODELS ---
class SolveEquationRequest(BaseModel):
    equation: str = Field(..., description="e.g. 'x**2 - 5*x + 6 = 0' or '2*x + 5 = 15'")
    variable: str = Field(default="x")


class CalculusRequest(BaseModel):
    expression: str = Field(..., description="e.g. 'sin(x)*cos(x)' or 'x**3 - 3*x + 1'")
    variable: str = Field(default="x")
    order: int = Field(default=1, ge=1, le=5)
    lower_limit: Optional[str] = None
    upper_limit: Optional[str] = None


class MatrixRequest(BaseModel):
    matrix: List[List[float]]
    operation: str = Field(default="determinant", description="determinant, inverse, eigenvalues, rref")


# --- SANDBOX MODELS ---
class CodeRunRequest(BaseModel):
    code: str = Field(..., min_length=1)
    timeout_seconds: float = Field(default=2.5, ge=0.5, le=10.0)


class DSATraceRequest(BaseModel):
    algorithm: str = Field(default="binary_search", description="binary_search, bubble_sort")
    array: List[int]
    target: Optional[int] = None


# --- SIMULATOR MODELS ---
class CPUScheduleRequest(BaseModel):
    algorithm: str = Field(default="fcfs", description="fcfs, round_robin")
    processes: List[Dict[str, Any]]
    quantum: int = Field(default=2, ge=1)


class BankerRequest(BaseModel):
    available: List[int]
    allocation: List[List[int]]
    max_matrix: List[List[int]]
    pids: Optional[List[str]] = None


class PageReplacementRequest(BaseModel):
    algorithm: str = Field(default="fifo", description="fifo, lru")
    pages: List[int]
    num_frames: int = Field(default=3, ge=1, le=10)


class SubnetRequest(BaseModel):
    ip_address: str
    prefix_length: int = Field(default=24, ge=8, le=32)


class TruthTableRequest(BaseModel):
    expression: str = Field(..., description="e.g. 'A and B or not C'")


# --- FLASHCARD & QUIZ MODELS ---
class DeckCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject_id: Optional[str] = None


class CardCreate(BaseModel):
    deck_id: str
    front: str
    back: str
    hints: Optional[str] = None
    explanation: Optional[str] = None


class CardReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=4, description="1=Again, 2=Hard, 3=Good, 4=Easy")


class QuizCreateRequest(BaseModel):
    title: str = Field(default="Academic Quiz")
    subject_id: Optional[str] = None
    difficulty: str = Field(default="medium")
    question_count: int = Field(default=5, ge=1, le=20)
    time_limit_minutes: int = Field(default=15, ge=1, le=120)


class QuizSubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(..., description="Mapping question_id -> user answer string")


# ==================== MATH ENDPOINTS ====================
@router.post("/math/solve", summary="Solve Algebraic Equation")
async def solve_equation(req: SolveEquationRequest):
    return math_engine.solve_equation(req.equation, req.variable)


@router.post("/math/diff", summary="Differentiate Expression")
async def differentiate_expr(req: CalculusRequest):
    return math_engine.differentiate(req.expression, req.variable, req.order)


@router.post("/math/integrate", summary="Integrate Expression")
async def integrate_expr(req: CalculusRequest):
    return math_engine.integrate(req.expression, req.variable, req.lower_limit, req.upper_limit)


@router.post("/math/simplify", summary="Simplify Expression")
async def simplify_expr(req: CalculusRequest):
    return math_engine.simplify(req.expression)


@router.post("/math/matrix", summary="Compute Matrix Operations")
async def compute_matrix(req: MatrixRequest):
    return math_engine.compute_matrix(req.matrix, req.operation)


# ==================== SANDBOX & DSA ENDPOINTS ====================
@router.post("/sandbox/run", summary="Safely Execute Code in Restricted Sandbox")
async def run_code(req: CodeRunRequest):
    sb = sandbox if req.timeout_seconds == sandbox.timeout_seconds else sandbox.__class__(req.timeout_seconds)
    return sb.execute(req.code)


@router.post("/dsa/trace", summary="Visual Algorithm Trace")
async def trace_algorithm(req: DSATraceRequest):
    if req.algorithm == "binary_search":
        target = req.target if req.target is not None else (req.array[0] if req.array else 0)
        return dsa_tracer.trace_binary_search(req.array, target)
    elif req.algorithm == "bubble_sort":
        return dsa_tracer.trace_bubble_sort(req.array)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported algorithm '{req.algorithm}'.")


# ==================== SIMULATORS ENDPOINTS ====================
@router.post("/simulators/cpu-schedule", summary="Simulate CPU Scheduling")
async def simulate_cpu(req: CPUScheduleRequest):
    if req.algorithm == "fcfs":
        return cpu_scheduler.simulate_fcfs(req.processes)
    elif req.algorithm == "round_robin":
        return cpu_scheduler.simulate_round_robin(req.processes, req.quantum)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported CPU algorithm '{req.algorithm}'.")


@router.post("/simulators/banker", summary="Banker's Deadlock Safety Simulation")
async def simulate_banker(req: BankerRequest):
    return bankers_simulator.simulate_safety(
        available=req.available,
        allocation=req.allocation,
        max_matrix=req.max_matrix,
        pids=req.pids,
    )


@router.post("/simulators/page-replacement", summary="Page Replacement Simulation")
async def simulate_page_replacement(req: PageReplacementRequest):
    if req.algorithm == "fifo":
        return page_simulator.simulate_fifo(req.pages, req.num_frames)
    elif req.algorithm == "lru":
        return page_simulator.simulate_lru(req.pages, req.num_frames)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported page algorithm '{req.algorithm}'.")


@router.post("/simulators/subnet", summary="IPv4 Subnet Calculator")
async def calculate_subnet(req: SubnetRequest):
    res = subnet_calculator.calculate_subnet(req.ip_address, req.prefix_length)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Invalid IP address or CIDR."))
    return res


@router.post("/simulators/truth-table", summary="Boolean Logic Truth Table")
async def generate_truth_table(req: TruthTableRequest):
    res = circuit_simulator.generate_truth_table(req.expression)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Invalid boolean expression."))
    return res


# ==================== FLASHCARDS & FSRS ENDPOINTS ====================
@router.get("/flashcards/decks", summary="List Flashcard Decks")
async def list_decks(db: AsyncSession = Depends(get_db)):
    stmt = select(FlashcardDeck).order_by(FlashcardDeck.created_at.desc())
    decks = (await db.execute(stmt)).scalars().all()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results = []
    for d in decks:
        total = await db.scalar(select(func.count(Flashcard.id)).where(Flashcard.deck_id == d.id)) or 0
        due = await db.scalar(
            select(func.count(Flashcard.id)).where(
                Flashcard.deck_id == d.id,
                (Flashcard.due_date <= today) | (Flashcard.due_date == None),
            )
        ) or 0
        results.append({
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "subject_id": d.subject_id,
            "total_cards": total,
            "due_cards": due,
            "created_at": d.created_at.isoformat(),
        })
    return results


@router.post("/flashcards/decks", status_code=status.HTTP_201_CREATED, summary="Create Flashcard Deck")
async def create_deck(data: DeckCreate, db: AsyncSession = Depends(get_db)):
    deck = FlashcardDeck(
        name=data.name,
        description=data.description,
        subject_id=data.subject_id,
    )
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return {"id": deck.id, "name": deck.name, "created_at": deck.created_at.isoformat()}


@router.delete("/flashcards/decks/{deck_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Flashcard Deck")
async def delete_deck(deck_id: str, db: AsyncSession = Depends(get_db)):
    deck = await db.scalar(select(FlashcardDeck).where(FlashcardDeck.id == deck_id))
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")
    await db.delete(deck)
    await db.commit()
    return None


@router.get("/flashcards/decks/{deck_id}/cards", summary="List Cards in Deck")
async def list_cards_in_deck(deck_id: str, due_only: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(Flashcard).where(Flashcard.deck_id == deck_id)
    if due_only:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stmt = stmt.where((Flashcard.due_date <= today) | (Flashcard.due_date == None))
    stmt = stmt.order_by(Flashcard.due_date.asc())
    cards = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": c.id,
            "deck_id": c.deck_id,
            "front": c.front,
            "back": c.back,
            "hints": c.hints,
            "explanation": c.explanation,
            "state": c.state,
            "difficulty": c.difficulty,
            "stability": c.stability,
            "reps": c.reps,
            "lapses": c.lapses,
            "scheduled_days": c.scheduled_days,
            "due_date": c.due_date,
        }
        for c in cards
    ]


@router.post("/flashcards/cards", status_code=status.HTTP_201_CREATED, summary="Create Flashcard")
async def create_card(data: CardCreate, db: AsyncSession = Depends(get_db)):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    card = Flashcard(
        deck_id=data.deck_id,
        front=data.front,
        back=data.back,
        hints=data.hints,
        explanation=data.explanation,
        state=0,
        difficulty=5.0,
        stability=1.0,
        reps=0,
        lapses=0,
        due_date=today,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return {"id": card.id, "deck_id": card.deck_id, "front": card.front, "due_date": card.due_date}


@router.post("/flashcards/cards/{card_id}/review", summary="Review Flashcard with FSRS Spaced Repetition")
async def review_card(card_id: str, req: CardReviewRequest, db: AsyncSession = Depends(get_db)):
    card = await db.scalar(select(Flashcard).where(Flashcard.id == card_id))
    if not card:
        raise HTTPException(status_code=404, detail="Card not found.")

    # Run FSRS calculation
    res = fsrs.schedule_review(
        rating=req.rating,
        state=card.state,
        current_difficulty=card.difficulty,
        current_stability=card.stability,
        reps=card.reps,
        lapses=card.lapses,
        elapsed_days=card.scheduled_days,
    )

    card.state = res["state"]
    card.difficulty = res["difficulty"]
    card.stability = res["stability"]
    card.reps = res["reps"]
    card.lapses = res["lapses"]
    card.scheduled_days = res["scheduled_days"]
    card.due_date = res["due_date"]

    # Log review
    log = ReviewLog(
        card_id=card.id,
        rating=req.rating,
        scheduled_days=res["scheduled_days"],
        elapsed_days=res["elapsed_days"],
    )
    db.add(log)
    await db.commit()

    return {
        "card_id": card.id,
        "rating": req.rating,
        "new_state": card.state,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "scheduled_days": card.scheduled_days,
        "due_date": card.due_date,
    }


# ==================== QUIZ ENDPOINTS ====================
@router.get("/quizzes", summary="List Quiz Sessions")
async def list_quizzes(db: AsyncSession = Depends(get_db)):
    stmt = select(QuizSession).order_by(QuizSession.created_at.desc())
    quizzes = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": q.id,
            "title": q.title,
            "subject_id": q.subject_id,
            "difficulty": q.difficulty,
            "total_questions": q.total_questions,
            "correct_count": q.correct_count,
            "score_percentage": q.score_percentage,
            "status": q.status,
            "created_at": q.created_at.isoformat(),
        }
        for q in quizzes
    ]


@router.post("/quizzes/generate", summary="Create / Generate Academic Quiz")
async def create_quiz(req: QuizCreateRequest, db: AsyncSession = Depends(get_db)):
    quiz = await quiz_engine.create_quiz(
        session=db,
        title=req.title,
        subject_id=req.subject_id,
        difficulty=req.difficulty,
        question_count=req.question_count,
        time_limit_minutes=req.time_limit_minutes,
    )
    return {
        "id": quiz.id,
        "title": quiz.title,
        "difficulty": quiz.difficulty,
        "total_questions": quiz.total_questions,
        "status": quiz.status,
    }


@router.get("/quizzes/{quiz_id}", summary="Get Quiz with Questions")
async def get_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)):
    quiz = await db.scalar(select(QuizSession).where(QuizSession.id == quiz_id))
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    q_stmt = select(QuizQuestion).where(QuizQuestion.session_id == quiz_id)
    questions = (await db.execute(q_stmt)).scalars().all()

    return {
        "id": quiz.id,
        "title": quiz.title,
        "difficulty": quiz.difficulty,
        "status": quiz.status,
        "total_questions": quiz.total_questions,
        "correct_count": quiz.correct_count,
        "score_percentage": quiz.score_percentage,
        "questions": [
            {
                "id": q.id,
                "question_type": q.question_type,
                "question_text": q.question_text,
                "options": q.options,
                "user_answer": q.user_answer,
                "is_correct": q.is_correct,
                "explanation": q.explanation if quiz.status == "completed" else None,
            }
            for q in questions
        ],
    }


@router.post("/quizzes/{quiz_id}/submit", summary="Submit Quiz Answers & Get Mistakes Review")
async def submit_quiz(quiz_id: str, req: QuizSubmitRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await quiz_engine.submit_quiz(session=db, quiz_id=quiz_id, answers=req.answers)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
