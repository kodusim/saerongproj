"""채팅 WebSocket 브로드캐스트.

연결 목록을 **프로세스 안에** 들고 있다. 그래서 uvicorn 워커는 1개여야 한다 —
워커가 여러 개면 다른 워커에 붙은 클라이언트에게 메시지가 가지 않는다.
늘리려면 Redis pub/sub 같은 프로세스 간 전달이 필요하다 (deploy/README.md 참고).

메시지 전송 자체는 HTTP POST /work/api/send/ 로 남겨둔다 (이미지 multipart 때문).
서버는 저장에 성공하면 이 허브로 모든 클라이언트에게 새 메시지를 밀어준다.
"""
import asyncio
import logging

from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger(__name__)


class ChatHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    @property
    def count(self) -> int:
        return len(self._clients)

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            targets = list(self._clients)

        dead = []
        for ws in targets:
            if ws.client_state is not WebSocketState.CONNECTED:
                dead.append(ws)
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                # 끊긴 소켓 — 조용히 정리한다
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)


hub = ChatHub()
