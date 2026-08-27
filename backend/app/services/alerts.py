from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class AlertHub:
    def __init__(self) -> None:
        self._clients: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._clients[user_id].append(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        peers = self._clients.get(user_id) or []
        if ws in peers:
            peers.remove(ws)

    async def push(self, user_id: int, payload: dict) -> None:
        living = []
        for ws in self._clients.get(user_id, []):
            try:
                await ws.send_json(payload)
                living.append(ws)
            except Exception:
                continue
        self._clients[user_id] = living


hub = AlertHub()
