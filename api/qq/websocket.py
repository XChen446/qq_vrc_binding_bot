import json
import asyncio
import logging
import websockets
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger("QQBot.WS")

class QQWebSocketManager:
    def __init__(self, ws_url: str, token: str = ""):
        self.ws_url = ws_url
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.on_message_callback: Optional[Callable[[Dict[str, Any]], asyncio.Task]] = None

    async def connect(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        while True:
            try:
                logger.info(f"正在连接到 NapCat: {self.ws_url}")
                async with websockets.connect(self.ws_url, additional_headers=headers) as ws:
                    self.ws = ws
                    logger.info("已连接到 NapCat WebSocket")
                    await self._listen()
            except Exception as e:
                logger.error(f"WebSocket 连接断开或错误: {e}")
                self.ws = None
                await asyncio.sleep(5)

    async def _listen(self):
        async for message in self.ws:
            try:
                data = json.loads(message)
                if self.on_message_callback:
                    asyncio.create_task(self.on_message_callback(data))
            except Exception as e:
                logger.error(f"解析 WebSocket 消息失败: {e}")

    async def send(self, data: Dict[str, Any]):
        if self.ws:
            await self.ws.send(json.dumps(data))
        else:
            logger.error("WebSocket 未连接，发送失败")
