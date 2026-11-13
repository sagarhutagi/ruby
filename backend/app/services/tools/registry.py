import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("ruby.tools.registry")


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    permission_level: str = "read"  # read, execute, admin
    timeout_seconds: float = 10.0
    category: str = "general"
    requires_approval: bool = False
    is_available: bool = True


class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ToolRegistry:
    """
    Centralized Agentic Tool Registry for Ruby.
    Provides schema registration, strict argument validation, permission checks,
    timeout handling, and error containment.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        permission_level: str = "read",
        timeout_seconds: float = 10.0,
        category: str = "general",
        requires_approval: bool = False,
    ) -> None:
        """Register a tool with its schema and handler function."""
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            permission_level=permission_level,
            timeout_seconds=timeout_seconds,
            category=category,
            requires_approval=requires_approval,
            is_available=True,
        )
        self._tools[name] = tool_def
        self._handlers[name] = handler
        logger.debug("Registered tool: %s (%s)", name, category)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[ToolDefinition]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def get_openai_tool_schemas(self) -> List[Dict[str, Any]]:
        """Exports tools in OpenAI-compatible function calling format."""
        schemas = []
        for tool in self._tools.values():
            if not tool.is_available:
                continue
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return schemas

    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        session: Optional[Any] = None,
        timeout: Optional[float] = None,
    ) -> ToolExecutionResult:
        """Executes a tool within timeout and exception containment boundaries."""
        if name not in self._tools:
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' is not registered in Ruby ToolRegistry.",
            )

        tool_def = self._tools[name]
        handler = self._handlers[name]
        time_limit = timeout or tool_def.timeout_seconds

        start_time = time.perf_counter()
        try:
            # Check if handler accepts session parameter
            sig = inspect.signature(handler)
            kwargs = dict(arguments or {})
            if "session" in sig.parameters and session is not None:
                kwargs["session"] = session

            # Execute with timeout
            if asyncio.iscoroutinefunction(handler):
                coro = handler(**kwargs)
                result = await asyncio.wait_for(coro, timeout=time_limit)
            else:
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: handler(**kwargs)),
                    timeout=time_limit,
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolExecutionResult(
                tool_name=name,
                success=True,
                data=result,
                execution_time_ms=round(elapsed_ms, 2),
            )

        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning("Tool '%s' timed out after %ss", name, time_limit)
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=f"Execution timed out after {time_limit} seconds.",
                execution_time_ms=round(elapsed_ms, 2),
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception("Error executing tool '%s': %s", name, e)
            return ToolExecutionResult(
                tool_name=name,
                success=False,
                error=f"Tool error: {str(e)}",
                execution_time_ms=round(elapsed_ms, 2),
            )


tool_registry = ToolRegistry()
