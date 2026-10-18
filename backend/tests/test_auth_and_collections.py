import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from tests.conftest import BACKEND_DIR


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    # /chat is not called here; stub the RAG engine so the vector store and models are not loaded.
    import types
    fake = types.ModuleType("app.RAG.hybrid_rag")
    fake.process_chat_query = lambda question, user_role: {
        "answer": "stub", "sources": [], "retrieval_type": "hybrid_rag", "role": user_role,
    }
    monkeypatch_module.setitem(sys.modules, "app.RAG.hybrid_rag", fake)
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def _token(client, username, password):
    res = client.post("/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_collections_requires_token(client):
    assert client.get("/collections/nurse").status_code == 401


def test_collections_rejects_forged_token(client):
    from jose import jwt
    forged = jwt.encode({"sub": "nurse.priya", "role": "admin"}, "medibot_secret_key_super_secure_2026", algorithm="HS256")
    assert client.get("/collections/admin", headers=_auth(forged)).status_code == 401


def test_collections_own_role(client):
    token = _token(client, "nurse.priya", "nurse")
    res = client.get("/collections/nurse", headers=_auth(token))
    assert res.status_code == 200
    assert res.json() == {"role": "nurse", "collections": ["nursing", "general"], "sql_rag_permitted": False}


def test_collections_other_role_forbidden(client):
    token = _token(client, "nurse.priya", "nurse")
    assert client.get("/collections/admin", headers=_auth(token)).status_code == 403


def test_collections_admin_may_read_any_role(client):
    token = _token(client, "admin.sys", "admin")
    res = client.get("/collections/billing_executive", headers=_auth(token))
    assert res.status_code == 200
    assert res.json()["sql_rag_permitted"] is True


def test_collections_unknown_role_for_admin_is_404(client):
    token = _token(client, "admin.sys", "admin")
    assert client.get("/collections/janitor", headers=_auth(token)).status_code == 404


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_chat_role_comes_from_token(client):
    token = _token(client, "nurse.priya", "nurse")
    res = client.post("/chat", json={"question": "hello"}, headers=_auth(token))
    assert res.status_code == 200
    assert res.json()["role"] == "nurse"


def test_chat_rejects_body_role_that_disagrees_with_token(client):
    token = _token(client, "nurse.priya", "nurse")
    res = client.post("/chat", json={"question": "hello", "role": "admin"}, headers=_auth(token))
    assert res.status_code == 403


def _start_app(env_overrides):
    env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
    env.update(env_overrides)
    # MEDIBOT_ENV_FILE points the settings at an empty file so the developer's real backend/.env is not read.
    return subprocess.run(
        [sys.executable, "-c", "import app.auth"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=60,
    )


@pytest.mark.parametrize("secret", [None, "", "short", "medibot_secret_key_super_secure_2026"])
def test_refuses_to_start_without_valid_secret(tmp_path, secret):
    env_file = tmp_path / ".env"
    env_file.write_text("")
    overrides = {"MEDIBOT_ENV_FILE": str(env_file)}
    if secret is not None:
        overrides["JWT_SECRET_KEY"] = secret
    proc = _start_app(overrides)
    assert proc.returncode != 0
    assert "JWT_SECRET_KEY" in proc.stderr


def test_reads_secret_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("JWT_SECRET_KEY=from-dotenv-file-0123456789abcdefgh\n")
    proc = _start_app({"MEDIBOT_ENV_FILE": str(env_file)})
    assert proc.returncode == 0, proc.stderr
