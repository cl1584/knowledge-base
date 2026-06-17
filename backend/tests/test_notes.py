"""基础测试：注册 → 登录 → 创建笔记 → 列表 → 删除"""
import pytest
from fastapi.testclient import TestClient

from app import app
from app.core.database import Base, engine, SessionLocal
from app.core.config import settings
from app.models import User

# 测试前清库
@pytest.fixture(autouse=True)
def clean_db():
    settings.sqlite_path.unlink(missing_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield
    # 测试后清理（可选）


client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_login_flow():
    # 注册
    r = client.post("/api/auth/register", json={
        "username": "testuser", "password": "testpass123", "nickname": "测试"
    })
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    user = r.json()["user"]
    assert user["username"] == "testuser"

    # 登录
    r = client.post("/api/auth/login", json={
        "username": "testuser", "password": "testpass123"
    })
    assert r.status_code == 200
    assert r.json()["access_token"] == token

    # 错误密码
    r = client.post("/api/auth/login", json={
        "username": "testuser", "password": "wrong"
    })
    assert r.status_code == 401


def test_notes_crud():
    # 注册拿 token
    r = client.post("/api/auth/register", json={
        "username": "alice", "password": "secret123"
    })
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 创建
    r = client.post("/api/notes", json={
        "title": "今天读了《思考，快与慢》",
        "content": "卡尼曼把思维分成系统1和系统2..."
    }, headers=headers)
    assert r.status_code == 200, r.text
    note = r.json()
    note_id = note["id"]
    assert note["title"] == "今天读了《思考，快与慢》"

    # 列表
    r = client.get("/api/notes", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["id"] == note_id

    # 详情
    r = client.get(f"/api/notes/{note_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == note_id

    # 更新
    r = client.patch(f"/api/notes/{note_id}", json={
        "content": "更新后的内容"
    }, headers=headers)
    assert r.status_code == 200
    assert r.json()["content"] == "更新后的内容"

    # 删除（软删）
    r = client.delete(f"/api/notes/{note_id}", headers=headers)
    assert r.status_code == 200

    # 列表（已删的看不到了）
    r = client.get("/api/notes", headers=headers)
    assert r.json()["total"] == 0


def test_unauth_access():
    # 不带 token 应该 401
    r = client.get("/api/notes")
    assert r.status_code == 401
