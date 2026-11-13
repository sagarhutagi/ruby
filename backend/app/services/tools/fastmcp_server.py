import logging
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP
from app.services.tools.builtins import (
    tool_calculate,
    tool_solve_equation,
    tool_execute_code,
    tool_trace_dsa,
    tool_get_system_info,
    tool_generate_quiz,
    tool_plot_function,
)

logger = logging.getLogger("ruby.tools.fastmcp")

# Initialize Ruby FastMCP Server
mcp_server = FastMCP(name="Ruby Academic Agent Tools")


@mcp_server.tool(name="calculate", description="Evaluate mathematical or algebraic expression using SymPy")
def mcp_calculate(expression: str) -> Dict[str, Any]:
    return tool_calculate(expression)


@mcp_server.tool(name="solve_equation", description="Solve algebraic equation for a variable")
def mcp_solve_equation(equation: str, variable: str = "x") -> Dict[str, Any]:
    return tool_solve_equation(equation, variable)


@mcp_server.tool(name="execute_code", description="Safely execute Python code in AST-verified sandbox")
def mcp_execute_code(code: str) -> Dict[str, Any]:
    return tool_execute_code(code)


@mcp_server.tool(name="trace_dsa", description="Step-by-step trace of binary search or bubble sort")
def mcp_trace_dsa(algorithm: str, array: List[int], target: Optional[int] = None) -> Dict[str, Any]:
    return tool_trace_dsa(algorithm, array, target)


@mcp_server.tool(name="get_system_info", description="Retrieve host hardware metrics (CPU, RAM, Disk)")
def mcp_get_system_info() -> Dict[str, Any]:
    return tool_get_system_info()


@mcp_server.tool(name="plot_function", description="Generate plot points for mathematical function f(x)")
def mcp_plot_function(function: str, x_min: float = -10.0, x_max: float = 10.0, num_points: int = 50) -> Dict[str, Any]:
    return tool_plot_function(function, x_min, x_max, num_points)


@mcp_server.tool(name="generate_quiz", description="Generate academic quiz questions for a topic")
def mcp_generate_quiz(subject: str = "Operating Systems", count: int = 3) -> Dict[str, Any]:
    return tool_generate_quiz(subject, count)
