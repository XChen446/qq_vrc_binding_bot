import logging
from typing import Dict, Any

logger = logging.getLogger("QQBot.EventRouter")


async def _handle_meta_event(data: Dict[str, Any]):
    """处理元事件 (如心跳)"""
    meta_type = data.get("meta_event_type")
    if meta_type == "heartbeat":
        pass
    elif meta_type == "lifecycle":
        sub_type = data.get("sub_type")
        logger.info(f"收到生命周期事件: {sub_type}")


class EventRouter:
    def __init__(self, bot):
        self.bot = bot
        # 注册事件处理映射
        self._handlers: Dict[str, any] = {
            "message": self._handle_message,
            "request": self._handle_request,
            "notice": self._handle_notice,
            "meta_event": _handle_meta_event
        }

    async def dispatch(self, data: Dict[str, Any]):
        """事件分发器"""
        try:
            # 1. 优先处理 API 响应 (Echo 包)
            if "echo" in data:
                self.bot.qq_client.handle_response(data)
                return

            # 2. 获取事件类型
            post_type = data.get("post_type")
            if not post_type:
                if "meta_event_type" in data:
                    post_type = "meta_event"
                else:
                    return

            # 3. 分发处理
            handler = self._handlers.get(post_type)
            if handler:
                await handler(data)
            else:
                logger.debug(f"未注册处理器的事件类型: {post_type}")

        except Exception as e:
            logger.error(f"事件分发异常: {e}", exc_info=True)

    async def _handle_message(self, data: Dict[str, Any]):
        """处理消息事件"""
        await self.bot.message_handler.handle_message(data)

    async def _handle_request(self, data: Dict[str, Any]):
        """处理请求事件"""
        await self.bot.group_handler.handle_request(data)

    async def _handle_notice(self, data: Dict[str, Any]):
        """处理通知事件"""
        await self.bot.group_handler.handle_notice(data)
