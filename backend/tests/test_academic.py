import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
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


def test_sympy_math_engine():
    """Verify symbolic equation solving, differentiation, integration, and matrix calculation."""
    # 1. Quadratic equation
    res_eq = math_engine.solve_equation("x**2 - 5*x + 6 = 0", "x")
    assert res_eq["success"] is True
    assert "2" in res_eq["solutions"]
    assert "3" in res_eq["solutions"]

    # 2. Differentiation
    res_diff = math_engine.differentiate("x**3 + 2*x", "x")
    assert res_diff["success"] is True
    assert "3*x**2 + 2" in res_diff["result"]

    # 3. Definite Integral
    res_int = math_engine.integrate("2*x", "x", lower_limit="0", upper_limit="3")
    assert res_int["success"] is True
    assert res_int["result"] == "9"

    # 4. Matrix determinant
    res_mat = math_engine.compute_matrix([[1, 2], [3, 4]], "determinant")
    assert res_mat["success"] is True
    assert res_mat["value"] == -2.0


def test_sandbox_safety_and_execution():
    """Verify code execution in sandbox, timeout enforcement, and security restriction against hostile imports."""
    # 1. Safe code execution
    safe_code = "print(sum([i * 2 for i in range(10)]))"
    res_safe = sandbox.execute(safe_code)
    assert res_safe["success"] is True
    assert "90" in res_safe["stdout"].strip()

    # 2. Hostile import rejection
    hostile_code = "import os\nos.system('echo hacked')"
    res_hostile = sandbox.execute(hostile_code)
    assert res_hostile["success"] is False
    assert "Security Exception" in res_hostile["error"]

    # 3. Timeout enforcement
    timeout_code = "while True: pass"
    res_timeout = sandbox.__class__(timeout_seconds=0.5).execute(timeout_code)
    assert res_timeout["success"] is False
    assert "Timed Out" in res_timeout["error"]


def test_dsa_algorithm_tracer():
    """Verify binary search and bubble sort step tracing."""
    # Binary Search
    bs_res = dsa_tracer.trace_binary_search([10, 20, 30, 40, 50, 60], 40)
    assert bs_res["found_index"] == 3
    assert bs_res["total_steps"] >= 1
    assert any(s["mid_value"] == 40 for s in bs_res["trace"])

    # Bubble Sort
    sort_res = dsa_tracer.trace_bubble_sort([5, 1, 4, 2])
    assert sort_res["sorted"] == [1, 2, 4, 5]
    assert len(sort_res["trace"]) > 0


def test_os_cpu_scheduler_simulation():
    """Verify FCFS and Round Robin scheduling Gantt chart generation and metrics."""
    procs = [
        {"pid": "P1", "arrival": 0, "burst": 4},
        {"pid": "P2", "arrival": 1, "burst": 3},
    ]

    # FCFS
    fcfs_res = cpu_scheduler.simulate_fcfs(procs)
    assert len(fcfs_res["gantt_chart"]) == 2
    assert fcfs_res["average_waiting_time"] > 0.0

    # Round Robin
    rr_res = cpu_scheduler.simulate_round_robin(procs, quantum=2)
    assert len(rr_res["gantt_chart"]) >= 3
    assert rr_res["average_turnaround_time"] > 0.0


def test_bankers_deadlock_avoidance():
    """Verify Banker's safety algorithm detects safe execution sequence."""
    available = [3, 3, 2]
    allocation = [
        [0, 1, 0],
        [2, 0, 0],
        [3, 0, 2],
        [2, 1, 1],
        [0, 0, 2],
    ]
    max_mat = [
        [7, 5, 3],
        [3, 2, 2],
        [9, 0, 2],
        [2, 2, 2],
        [4, 3, 3],
    ]
    pids = ["P0", "P1", "P2", "P3", "P4"]

    res = bankers_simulator.simulate_safety(available, allocation, max_mat, pids)
    assert res["is_safe"] is True
    assert len(res["safe_sequence"]) == 5
    assert "P1" in res["safe_sequence"]


def test_page_replacement_simulation():
    """Verify FIFO and LRU page replacement faults and hits."""
    pages = [7, 0, 1, 2, 0, 3, 0, 4]
    res_fifo = page_simulator.simulate_fifo(pages, num_frames=3)
    assert res_fifo["page_faults"] > 0
    assert res_fifo["page_hits"] > 0

    res_lru = page_simulator.simulate_lru(pages, num_frames=3)
    assert res_lru["page_faults"] > 0


def test_subnet_calculator():
    """Verify IPv4 subnet network ID, broadcast, and host count calculation."""
    res = subnet_calculator.calculate_subnet("192.168.1.100", 24)
    assert res["success"] is True
    assert res["network_address"] == "192.168.1.0"
    assert res["broadcast_address"] == "192.168.1.255"
    assert res["usable_hosts"] == 254


def test_dlcd_truth_table():
    """Verify boolean logic truth table and minterms notation."""
    res = circuit_simulator.generate_truth_table("A and B or not C")
    assert res["success"] is True
    assert len(res["table"]) == 8  # 3 variables -> 2^3 = 8 rows
    assert len(res["minterms"]) > 0


def test_fsrs_spaced_repetition():
    """Verify FSRS review interval updates and forgetting curve calculation."""
    # First review with Good (3)
    r_first = fsrs.schedule_review(rating=3, state=0)
    assert r_first["state"] == 2
    assert r_first["scheduled_days"] >= 1
    assert r_first["due_date"] is not None

    # Lapse review with Again (1)
    r_lapse = fsrs.schedule_review(
        rating=1,
        state=2,
        current_difficulty=5.0,
        current_stability=4.0,
        reps=3,
        lapses=0,
    )
    assert r_lapse["state"] == 3  # Relearning
    assert r_lapse["stability"] < 4.0
    assert r_lapse["lapses"] == 1


@pytest.mark.asyncio
async def test_academic_api_endpoints(client: AsyncClient, session: AsyncSession):
    """Verify HTTP API endpoints for math, simulators, flashcards, and quizzes."""
    # 1. Math endpoint
    math_res = await client.post(
        "/api/v1/academic/math/solve",
        json={"equation": "3*x - 12 = 0", "variable": "x"},
    )
    assert math_res.status_code == 200
    assert "4" in math_res.json()["solutions"]

    # 2. Flashcard Deck & Review
    deck_res = await client.post(
        "/api/v1/academic/flashcards/decks",
        json={"name": "OS Architecture", "description": "Kernel and Processes"},
    )
    assert deck_res.status_code == 201
    deck_id = deck_res.json()["id"]

    card_res = await client.post(
        "/api/v1/academic/flashcards/cards",
        json={
            "deck_id": deck_id,
            "front": "What is a PCB in an Operating System?",
            "back": "Process Control Block: Data structure storing process state, PC, and registers.",
        },
    )
    assert card_res.status_code == 201
    card_id = card_res.json()["id"]

    # Review card
    rev_res = await client.post(
        f"/api/v1/academic/flashcards/cards/{card_id}/review",
        json={"rating": 3},
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["new_state"] == 2

    # 3. Quiz Generation & Submission
    quiz_res = await client.post(
        "/api/v1/academic/quizzes/generate",
        json={"title": "Midterm Review Quiz", "question_count": 3},
    )
    assert quiz_res.status_code == 200
    quiz_id = quiz_res.json()["id"]

    # Fetch quiz
    fetch_quiz = await client.get(f"/api/v1/academic/quizzes/{quiz_id}")
    assert fetch_quiz.status_code == 200
    q_data = fetch_quiz.json()
    assert len(q_data["questions"]) >= 1

    # List quizzes
    list_q_res = await client.get("/api/v1/academic/quizzes")
    assert list_q_res.status_code == 200
    assert any(q["id"] == quiz_id for q in list_q_res.json())

    # Check cards list with due_only
    cards_res = await client.get(f"/api/v1/academic/flashcards/decks/{deck_id}/cards?due_only=false")
    assert cards_res.status_code == 200
    assert len(cards_res.json()) == 1

    # Submit quiz answers
    first_q = q_data["questions"][0]
    sub_res = await client.post(
        f"/api/v1/academic/quizzes/{quiz_id}/submit",
        json={"answers": {first_q["id"]: "False"}},
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "completed"
    assert "mistakes_review" in sub_data

    # Cleanup
    await client.delete(f"/api/v1/academic/flashcards/decks/{deck_id}")
