from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from app.core.config import settings

logger = logging.getLogger("ruby.agent.permissions")

PermissionEffect = Literal["allow", "deny", "ask"]


@dataclass
class PermissionRule:
    action: str  # wildcard match, e.g. "read", "execute_python_code", "web_search", "*"
    resource: str  # wildcard match, e.g. "*", "*.py", "/home/mars/**"
    effect: PermissionEffect  # "allow", "deny", "ask"
    description: Optional[str] = None


@dataclass
class PermissionRequest:
    request_id: str
    action: str
    resource: str
    tool_name: str
    arguments: Dict[str, Any]
    description: str
    created_at: float = field(default_factory=time.time)


class PermissionManager:
    """
    Evaluates fine-grained action:resource permission rules and intercepts
    tool executions requiring user approval via async deferred futures.
    Inspired by OpenCode's permission engine.
    """

    DEFAULT_RULES: List[PermissionRule] = [
        PermissionRule("read", "*", "allow", "Allow all read actions"),
        PermissionRule("document_search", "*", "allow", "Allow document search"),
        PermissionRule("web_search", "*", "allow", "Allow SearXNG web search"),
        PermissionRule("math_*", "*", "allow", "Allow SymPy mathematics"),
        PermissionRule("solve_equation", "*", "allow", "Allow SymPy equation solving"),
        PermissionRule("dsa_*", "*", "allow", "Allow DSA simulator traces"),
        PermissionRule("dsa_trace", "*", "allow", "Allow DSA simulator traces"),
        PermissionRule("save_memory", "*", "allow", "Allow saving academic memories"),
        PermissionRule("query_academic_records", "*", "allow", "Allow querying student marks and grades"),
        PermissionRule("compare_academic_assessments", "*", "allow", "Allow assessment comparison"),
        PermissionRule("get_academic_performance_summary", "*", "allow", "Allow performance summary and trends"),
        PermissionRule("get_gpu_stats", "*", "allow", "Allow hardware telemetry"),
        PermissionRule("get_system_info", "*", "allow", "Allow system information"),
        PermissionRule("execute_python_code", "*", "ask", "Ask before executing arbitrary Python code"),
        PermissionRule("write_file", "*", "ask", "Ask before modifying local filesystem"),
        PermissionRule("shell_command", "*", "deny", "Deny direct unsandboxed shell execution by default"),
    ]

    def __init__(self, custom_rules: Optional[List[PermissionRule]] = None):
        self._rules: List[PermissionRule] = list(self.DEFAULT_RULES)
        if custom_rules:
            self._rules.extend(custom_rules)
        self._pending_requests: Dict[str, asyncio.Future[bool]] = {}
        self._request_metadata: Dict[str, PermissionRequest] = {}

    def add_rule(self, rule: PermissionRule) -> None:
        """Adds a rule with highest precedence (evaluated in reverse order)."""
        self._rules.append(rule)

    def evaluate(self, action: str, resource: str = "*") -> PermissionEffect:
        """
        Evaluates action and resource against active rulesets using wildcard matching.
        The last matching rule determines the outcome. Defaults to 'ask'.
        """
        for rule in reversed(self._rules):
            if fnmatch.fnmatch(action, rule.action) and fnmatch.fnmatch(resource, rule.resource):
                return rule.effect
        return "ask"

    def get_pending_requests(self) -> List[PermissionRequest]:
        return list(self._request_metadata.values())

    async def check_or_request_approval(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        resource: str = "*",
        description: Optional[str] = None,
        request_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> bool:
        """
        Evaluates permissions for a tool invocation.
        - If 'allow': returns True immediately.
        - If 'deny': returns False immediately.
        - If 'ask': creates an async Future and awaits user resolution via UI.
        """
        effect = self.evaluate(tool_name, resource)
        if effect == "allow":
            return True
        if effect == "deny":
            logger.warning("Permission denied for action='%s', resource='%s'", tool_name, resource)
            return False

        req_id = request_id or str(uuid.uuid4())
        desc = description or f"Tool '{tool_name}' requested execution with arguments: {str(arguments)[:100]}"
        req = PermissionRequest(
            request_id=req_id,
            action=tool_name,
            resource=resource,
            tool_name=tool_name,
            arguments=arguments,
            description=desc,
        )

        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._pending_requests[req_id] = future
        self._request_metadata[req_id] = req

        timeout = timeout_seconds or settings.agent_approval_timeout_seconds
        logger.info("Permission 'ask' triggered for %s (request_id=%s, timeout=%.1fs)", tool_name, req_id, timeout)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Permission request %s timed out after %.1fs; denied by default", req_id, timeout)
            return False
        finally:
            self._pending_requests.pop(req_id, None)
            self._request_metadata.pop(req_id, None)

    def resolve_approval(
        self,
        request_id: str,
        approved: bool,
        remember: bool = False,
    ) -> bool:
        """
        Resolves an active pending permission request.
        If remember=True, adds a persistent rule allowing or denying this action.
        """
        if request_id not in self._pending_requests:
            logger.warning("Attempted to resolve nonexistent permission request: %s", request_id)
            return False

        future = self._pending_requests[request_id]
        req = self._request_metadata.get(request_id)

        if not future.done():
            future.set_result(approved)

        if remember and req:
            new_effect: PermissionEffect = "allow" if approved else "deny"
            self.add_rule(PermissionRule(
                action=req.action,
                resource=req.resource,
                effect=new_effect,
                description=f"User remembered preference for {req.action}:{req.resource}",
            ))
            logger.info("Saved persistent permission rule: %s on %s -> %s", req.action, req.resource, new_effect)

        return True


# Global default permission manager instance
permission_manager = PermissionManager()
