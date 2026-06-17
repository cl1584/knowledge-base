"""User settings API：AI 配置（每用户独立）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models import User
from app.schemas import AISettingsUpdate, AISettingsResponse

router = APIRouter()


@router.get("/me/ai-settings", response_model=AISettingsResponse)
def get_ai_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的 AI 设置（不含 key 明文）"""
    return AISettingsResponse(
        has_key=bool(current_user.ai_api_key and current_user.ai_api_key.strip()),
        base_url=current_user.ai_base_url or "",
        model=current_user.ai_model or "",
    )


@router.post("/me/ai-settings")
def update_ai_settings(
    req: AISettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存当前用户的 AI 设置"""
    if req.api_key is not None:
        current_user.ai_api_key = req.api_key
    current_user.ai_base_url = req.base_url or ""
    current_user.ai_model = req.model or ""
    db.commit()
    return {"ok": True, "has_key": bool(current_user.ai_api_key)}
