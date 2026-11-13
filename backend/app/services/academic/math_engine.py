import sympy as sp
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("ruby.academic.math")


class SymPyMathEngine:
    """
    Academic Mathematics & Symbolic Engine.
    Provides verified calculations, derivations, equation solving,
    and LaTeX formatting without relying on LLM arithmetic hallucinations.
    """

    @staticmethod
    def solve_equation(equation_str: str, var_str: str = "x") -> Dict[str, Any]:
        """
        Solves algebraic equation f(x) = 0 or expr1 = expr2 for the target variable.
        """
        try:
            var = sp.Symbol(var_str)
            if "=" in equation_str:
                lhs_str, rhs_str = equation_str.split("=", 1)
                lhs = sp.sympify(lhs_str.strip())
                rhs = sp.sympify(rhs_str.strip())
                eq = sp.Eq(lhs, rhs)
                solutions = sp.solve(eq, var)
            else:
                expr = sp.sympify(equation_str.strip())
                eq = sp.Eq(expr, 0)
                solutions = sp.solve(expr, var)

            latex_eq = sp.latex(eq)
            latex_sols = [sp.latex(s) for s in solutions]

            return {
                "success": True,
                "variable": var_str,
                "equation_latex": f"$${latex_eq}$$",
                "solutions": [str(s) for s in solutions],
                "solutions_latex": f"$${var_str} \\in \\{{{', '.join(latex_sols)}\\}}$$",
                "steps": [
                    f"Parsed equation: {latex_eq}",
                    f"Identified variable to isolate: ${var_str}$",
                    f"Computed {len(solutions)} solution(s).",
                ],
            }
        except Exception as e:
            logger.warning("SymPy equation solve failed for '%s': %s", equation_str, e)
            return {"success": False, "error": str(e)}

    @staticmethod
    def differentiate(expr_str: str, var_str: str = "x", order: int = 1) -> Dict[str, Any]:
        """Calculates n-th derivative of expression with respect to variable."""
        try:
            var = sp.Symbol(var_str)
            expr = sp.sympify(expr_str.strip())
            derivative = sp.diff(expr, var, order)

            orig_latex = sp.latex(expr)
            diff_latex = sp.latex(derivative)
            d_op = f"\\frac{{d^{{{order}}}}}{{d{var_str}^{{{order}}}}}" if order > 1 else f"\\frac{{d}}{{d{var_str}}}"

            return {
                "success": True,
                "order": order,
                "variable": var_str,
                "original_latex": f"$${orig_latex}$$",
                "derivative_latex": f"$${d_op}\\left({orig_latex}\\right) = {diff_latex}$$",
                "result": str(derivative),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def integrate(
        expr_str: str,
        var_str: str = "x",
        lower_limit: Optional[str] = None,
        upper_limit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates definite or indefinite integral."""
        try:
            var = sp.Symbol(var_str)
            expr = sp.sympify(expr_str.strip())

            orig_latex = sp.latex(expr)

            if lower_limit is not None and upper_limit is not None:
                a = sp.sympify(lower_limit.strip())
                b = sp.sympify(upper_limit.strip())
                integral = sp.integrate(expr, (var, a, b))
                int_latex = sp.latex(integral)
                display_latex = f"$$\\int_{{{sp.latex(a)}}}^{{{sp.latex(b)}}} \\left({orig_latex}\\right) d{var_str} = {int_latex}$$"
            else:
                integral = sp.integrate(expr, var)
                int_latex = sp.latex(integral)
                display_latex = f"$$\\int \\left({orig_latex}\\right) d{var_str} = {int_latex} + C$$"

            return {
                "success": True,
                "is_definite": lower_limit is not None,
                "original_latex": f"$${orig_latex}$$",
                "integral_latex": display_latex,
                "result": str(integral),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def simplify(expr_str: str) -> Dict[str, Any]:
        """Simplifies algebraic or trigonometric expression."""
        try:
            expr = sp.sympify(expr_str.strip())
            simplified = sp.simplify(expr)
            return {
                "success": True,
                "original_latex": f"$${sp.latex(expr)}$$",
                "simplified_latex": f"$${sp.latex(simplified)}$$",
                "result": str(simplified),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def compute_matrix(matrix_rows: List[List[float]], operation: str = "determinant") -> Dict[str, Any]:
        """Performs matrix operations: determinant, inverse, eigenvalues, rref."""
        try:
            mat = sp.Matrix(matrix_rows)
            mat_latex = sp.latex(mat)

            if operation == "determinant":
                det = mat.det()
                return {
                    "success": True,
                    "operation": "determinant",
                    "matrix_latex": f"$${mat_latex}$$",
                    "result_latex": f"$$\\det(A) = {sp.latex(det)}$$",
                    "value": float(det) if det.is_number else str(det),
                }
            elif operation == "inverse":
                if mat.det() == 0:
                    return {"success": False, "error": "Matrix is singular (determinant is 0), inverse does not exist."}
                inv = mat.inv()
                return {
                    "success": True,
                    "operation": "inverse",
                    "matrix_latex": f"$${mat_latex}$$",
                    "result_latex": f"$$A^{{-1}} = {sp.latex(inv)}$$",
                }
            elif operation == "eigenvalues":
                eigs = mat.eigenvals()
                eigs_latex = ", ".join(f"\\lambda = {sp.latex(k)} \\text{{ (mult: {v})}}" for k, v in eigs.items())
                return {
                    "success": True,
                    "operation": "eigenvalues",
                    "matrix_latex": f"$${mat_latex}$$",
                    "result_latex": f"$${eigs_latex}$$",
                }
            elif operation == "rref":
                rref_mat, pivots = mat.rref()
                return {
                    "success": True,
                    "operation": "rref",
                    "matrix_latex": f"$${mat_latex}$$",
                    "result_latex": f"$$\\text{{RREF}}(A) = {sp.latex(rref_mat)}$$",
                    "pivots": pivots,
                }
            else:
                return {"success": False, "error": f"Unsupported matrix operation: {operation}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


math_engine = SymPyMathEngine()
