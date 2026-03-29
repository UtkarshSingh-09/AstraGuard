from fastapi import APIRouter

from app.repositories.users_repo import UsersRepository
from app.services.arth_score_service import calculate_arth_score

router = APIRouter(prefix="/api", tags=["arth"])
users_repo = UsersRepository()


@router.get("/arth-score/{user_id}")
async def get_arth_score(user_id: str):
    user = await users_repo.get_user(user_id)
    score = calculate_arth_score(user)
    return {
        "user_id": user_id,
        "arth_score": score,
    }
