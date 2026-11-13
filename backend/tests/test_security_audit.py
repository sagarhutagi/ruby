import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.academic.sandbox import sandbox
from app.services.obsidian.exporter import validate_safe_export_path
from app.core.config import settings


@pytest.mark.asyncio
async def test_upload_rejection_for_unsupported_extensions(client: AsyncClient):
    """Verify malicious or unsupported scripts (.sh, .exe) are rejected during upload."""
    malicious_file = ("script.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh")
    res = await client.post(
        "/api/v1/documents/upload",
        files=[("files", malicious_file)],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    assert data[0]["status"] == "failed"
    assert "Unsupported or restricted file format" in data[0]["message"]


@pytest.mark.asyncio
async def test_obsidian_vault_path_traversal_guards():
    """Verify attempt to export to root system directories raises security ValueError."""
    for dangerous_path in ["/etc", "/etc/cron.daily", "/root/.ssh", "/usr/bin", "/sys/kernel"]:
        with pytest.raises(ValueError) as excinfo:
            validate_safe_export_path(dangerous_path)
        assert "inside a protected system directory" in str(excinfo.value)


@pytest.mark.asyncio
async def test_obsidian_api_path_traversal_returns_400(client: AsyncClient):
    """Verify HTTP API returns 400 when attempting vault export to protected system dirs."""
    res = await client.post(
        "/api/v1/graph/obsidian/preview",
        json={"vault_path": "/etc/malicious_vault"},
    )
    assert res.status_code == 400
    assert "protected system directory" in res.json()["detail"]


def test_sandbox_ast_reflection_and_dunder_blocking():
    """Verify code sandbox rejects Python introspection and dunder escape exploits."""
    # Exploit 1: getattr on module
    exploit_getattr = 'getattr(__import__("o" + "s"), "system")("id")'
    err1 = sandbox.validate_code_safety(exploit_getattr)
    assert err1 is not None
    assert "Security Exception" in err1

    # Exploit 2: Subclasses traversal
    exploit_subclasses = "().__class__.__base__.__subclasses__()"
    err2 = sandbox.validate_code_safety(exploit_subclasses)
    assert err2 is not None
    assert "Security Exception" in err2
    assert "__subclasses__" in err2 or "__class__" in err2

    # Exploit 3: globals inspection
    exploit_globals = "g = globals()['__builtins__']"
    err3 = sandbox.validate_code_safety(exploit_globals)
    assert err3 is not None
    assert "Security Exception" in err3


def test_sandbox_timeout_containment():
    """Verify CPU-intensive infinite loops trigger timeout safely."""
    infinite_loop = "while True:\n    pass\n"
    res = sandbox.execute(infinite_loop)
    assert res["success"] is False
    assert "timed out" in res["error"].lower()


@pytest.mark.asyncio
async def test_secret_protection_in_all_endpoints(client: AsyncClient):
    """Verify secrets are never leaked in diagnostic reports or provider listings."""
    # 1. Providers endpoint
    prov_res = await client.get("/api/v1/providers")
    assert prov_res.status_code == 200
    prov_text = prov_res.text
    assert "sk-" not in prov_text or "sk-..." in prov_text  # only masked allowed

    # 2. Diagnostic export
    diag_res = await client.get("/api/v1/analytics/diagnostics")
    assert diag_res.status_code == 200
    diag_text = diag_res.text
    assert "sk-proj-" not in diag_text


def test_localhost_network_binding_policy():
    """Verify strict localhost binding and CORS policy in settings."""
    assert settings.host in ["127.0.0.1", "localhost"]
    for origin in settings.cors_origins:
        assert "127.0.0.1" in origin or "localhost" in origin
