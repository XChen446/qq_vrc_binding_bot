import json
import asyncio
import logging
import websockets
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger("QQBot.WS")

class QQWebSocketManager:
    def __init__(self, ws_url: str, token: str = "", max_retries: int = 10, initial_delay: float = 5.0, max_delay: float = 60.0):
        self.ws_url = ws_url
        self.token = token
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.on_message_callback: Optional[Callable[[Dict[str, Any]], asyncio.Task]] = None
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.retry_count = 0
        self._should_stop = False
        self._auth_error = False

    async def connect(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        while not self._should_stop:
            if self._auth_error:
                logger.error("检测到认证错误，停止重连。请检查 token 配置后重启服务")
                break
            
            if self.retry_count >= self.max_retries:
                logger.error(f"已达到最大重连次数 ({self.max_retries})，停止重连")
                break
            
            try:
                logger.info(f"正在连接到 NapCat: {self.ws_url} (重连: {self.retry_count}/{self.max_retries})")
                async with websockets.connect(self.ws_url, additional_headers=headers) as ws:
                    self.ws = ws
                    self.retry_count = 0
                    await self._listen()
            except Exception as e:
                if self._auth_error:
                    logger.error(f"认证错误，停止重连: {e}")
                    break
                
                self.retry_count += 1
                logger.error(f"WebSocket 连接断开或错误: {e}")
                self.ws = None
                
                delay = min(self.initial_delay * (2 ** (self.retry_count - 1)), self.max_delay)
                logger.info(f"{delay:.1f} 秒后重试...")
                await asyncio.sleep(delay)

    async def disconnect(self):
        self._should_stop = True
        if self.ws:
            try:
                await self.ws.close()
                logger.info("WebSocket 连接已关闭")
            except Exception as e:
                logger.error(f"关闭 WebSocket 连接时出错: {e}")
        self._auth_error = False

    async def _listen(self):
        first_message = True
        async for message in self.ws:
            try:
                data = json.loads(message)
                retcode = data.get("retcode")
                
                if retcode == 1403:
                    self._auth_error = True
                    logger.error("Token 验证失败，请检查配置中的 token")
                    raise Exception("Token 验证失败")
                
                if first_message:
                    logger.info("WebSocket 认证成功，开始监听消息")
                    first_message = False
                
                if self.on_message_callback:
                    asyncio.create_task(self.on_message_callback(data))
            except Exception as e:
                logger.error(f"解析 WebSocket 消息失败: {e}")
                raise

    async def send(self, data: Dict[str, Any]):
        if self.ws:
            await self.ws.send(json.dumps(data))
        else:
            logger.error("WebSocket 未连接，发送失败")
