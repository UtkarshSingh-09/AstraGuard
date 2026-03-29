from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.repositories.sessions_repo import SessionsRepository
from app.repositories.users_repo import UsersRepository

from agents.orchestrator import run_orchestrator

router = APIRouter(tags=["onboard"])
sessions_repo = SessionsRepository()
users_repo = UsersRepository()


class OnboardRequest(BaseModel):
    session_id: str = Field(..., min_length=3)
    conversation_history: list[dict] = Field(default_factory=list)
    extraction_complete: bool = False
    user_id: str | None = None


@router.post("/api/onboard")
async def onboard(request: OnboardRequest):
    latest_user_msg = ""
    for msg in reversed(request.conversation_history):
        if msg.get("role") == "user":
            latest_user_msg = str(msg.get("content", ""))
            break
            
    if latest_user_msg:
        await sessions_repo.append_conversation(request.session_id, request.user_id, "user", latest_user_msg)
        
    user = None
    if request.user_id:
        user = await users_repo.get_user(request.user_id)
        
    response = await run_orchestrator(
        user_id=request.user_id or "anonymous",
        message=latest_user_msg or "start onboarding",
        session_id=request.session_id,
        conversation_history=request.conversation_history,
        financial_dna=user.get("financial_dna") if user else None,
        behavioral_dna=user.get("behavioral_dna") if user else None,
        force_intent="onboard",
    )

    extracted_so_far = response.get("extracted_so_far", {})
    completion_percentage = response.get("completion_percentage", 0)
    
    await sessions_repo.set_extracted_data(
        request.session_id,
        extracted_so_far,
        completion_percentage,
    )
    
    if request.user_id:
        await users_repo.upsert_user(
            request.user_id,
            {"last_session_id": request.session_id},
        )
        
    return response


@router.post("/api/chat")
async def chat_alias(request: OnboardRequest):
    return await onboard(request)
