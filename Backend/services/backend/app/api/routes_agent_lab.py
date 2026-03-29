from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

router = APIRouter(tags=["agent_lab"])


@router.get("/agent-lab", response_class=HTMLResponse)
async def agent_lab():
    page = Path(__file__).resolve().parents[4] / "tools" / "agent_lab" / "index.html"
    if not page.exists():
        return HTMLResponse("<h3>Agent Lab not found</h3>", status_code=404)
    return FileResponse(str(page))
