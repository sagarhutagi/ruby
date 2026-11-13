import ast
import time
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ruby.academic.sandbox")

BANNED_MODULES = {
    "os", "sys", "subprocess", "socket", "urllib", "requests", "httpx",
    "shutil", "pty", "posix", "ctypes", "multiprocessing", "threading",
    "signal", "pathlib", "builtins", "importlib",
}

BANNED_CALLS = {
    "eval", "exec", "open", "__import__", "compile", "globals", "locals",
}


class CodeSandbox:
    """
    Restricted Python Execution Sandbox for academic algorithm dry-runs.
    Guarantees isolation with static AST verification, timeout boundaries,
    and temporary workspace cleanup.
    """

    def __init__(self, timeout_seconds: float = 2.5):
        self.timeout_seconds = timeout_seconds

    def validate_code_safety(self, code: str) -> Optional[str]:
        """Performs static AST analysis to reject unauthorized system calls or network imports."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax Error: {e.msg} (line {e.lineno})"

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in BANNED_MODULES:
                        return f"Security Exception: Import of module '{root_pkg}' is restricted in sandbox."
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg in BANNED_MODULES:
                        return f"Security Exception: Import from module '{root_pkg}' is restricted in sandbox."

            # Check banned function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in BANNED_CALLS:
                        return f"Security Exception: Builtin '{node.func.id}()' is prohibited in sandbox."

        return None

    def execute(self, code: str) -> Dict[str, Any]:
        """Safely executes user/algorithm code in a bounded subprocess."""
        # 1. Static validation
        safety_error = self.validate_code_safety(code)
        if safety_error:
            return {
                "success": False,
                "error": safety_error,
                "stdout": "",
                "stderr": safety_error,
                "execution_time_ms": 0.0,
                "is_sandboxed": True,
            }

        # 2. Run in isolated temporary directory
        start_time = time.perf_counter()
        with tempfile.TemporaryDirectory() as sandbox_dir:
            script_path = Path(sandbox_dir) / "run.py"
            script_path.write_text(code, encoding="utf-8")

            try:
                proc = subprocess.run(
                    ["python3", str(script_path)],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    env={"PYTHONPATH": "", "LANG": "C.UTF-8"},  # Clean minimal environment
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                return {
                    "success": (proc.returncode == 0),
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "execution_time_ms": round(elapsed_ms, 2),
                    "is_sandboxed": True,
                }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": f"Execution Timed Out: Code exceeded time limit of {self.timeout_seconds}s.",
                    "stdout": "",
                    "stderr": "TimeoutExpired",
                    "execution_time_ms": self.timeout_seconds * 1000.0,
                    "is_sandboxed": True,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Execution failure: {str(e)}",
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time_ms": 0.0,
                    "is_sandboxed": True,
                }


class DSATracer:
    """Provides step-by-step visual algorithmic traces for academic demonstrations."""

    @staticmethod
    def trace_binary_search(arr: List[int], target: int) -> Dict[str, Any]:
        sorted_arr = sorted(arr)
        steps = []
        low = 0
        high = len(sorted_arr) - 1
        found_idx = -1

        step_num = 1
        while low <= high:
            mid = (low + high) // 2
            mid_val = sorted_arr[mid]

            steps.append({
                "step": step_num,
                "low": low,
                "mid": mid,
                "high": high,
                "array": list(sorted_arr),
                "mid_value": mid_val,
                "comparison": f"arr[{mid}] = {mid_val} vs target {target}",
                "action": "Found target!" if mid_val == target else ("Search right half" if mid_val < target else "Search left half"),
            })

            if mid_val == target:
                found_idx = mid
                break
            elif mid_val < target:
                low = mid + 1
            else:
                high = mid - 1
            step_num += 1

        return {
            "algorithm": "Binary Search",
            "time_complexity": "O(log n)",
            "space_complexity": "O(1)",
            "sorted_array": sorted_arr,
            "target": target,
            "found_index": found_idx,
            "total_steps": len(steps),
            "trace": steps,
        }

    @staticmethod
    def trace_bubble_sort(arr: List[int]) -> Dict[str, Any]:
        data = list(arr)
        n = len(data)
        steps = []
        step_num = 1

        for i in range(n):
            swapped = False
            for j in range(0, n - i - 1):
                cmp_str = f"Compare arr[{j}]={data[j]} with arr[{j+1}]={data[j+1]}"
                if data[j] > data[j + 1]:
                    data[j], data[j + 1] = data[j + 1], data[j]
                    swapped = True
                    action = f"Swap elements -> {data[j]} and {data[j+1]}"
                else:
                    action = "In order, no swap"

                steps.append({
                    "step": step_num,
                    "indices": [j, j + 1],
                    "comparison": cmp_str,
                    "action": action,
                    "array_state": list(data),
                })
                step_num += 1

            if not swapped:
                break

        return {
            "algorithm": "Bubble Sort",
            "time_complexity": "O(n^2) worst/avg, O(n) best",
            "space_complexity": "O(1)",
            "initial": arr,
            "sorted": data,
            "total_steps": len(steps),
            "trace": steps[:50],  # cap at 50 for clean UI rendering
        }


sandbox = CodeSandbox()
dsa_tracer = DSATracer()
