from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_service import ws_manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect(user_id, websocket)
    await websocket.send_json({"type": "connected", "data": {"user_id": user_id}})
    try:
        while True:
            incoming = await websocket.receive_text()
            await ws_manager.send_to_user(
                user_id,
                {"type": "echo", "data": {"message": incoming}},
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
    except Exception:
        ws_manager.disconnect(user_id, websocket)
