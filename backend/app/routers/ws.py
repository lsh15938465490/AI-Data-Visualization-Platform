from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.services.alerts import hub

router = APIRouter()


@router.websocket("/api/ws/alerts")
async def alerts_socket(ws: WebSocket, token: str = ""):
    if not token:
        await ws.close(code=4401)
        return
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username = payload.get("sub")
    except JWTError:
        await ws.close(code=4401)
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
    finally:
        db.close()
    if not user:
        await ws.close(code=4401)
        return
    await hub.connect(user.id, ws)
    try:
        await ws.send_json({"type": "ready", "message": "告警通道已连接"})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(user.id, ws)
