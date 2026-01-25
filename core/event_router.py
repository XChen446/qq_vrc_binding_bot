import logging
from typing import Dict, Any

logger = logging.getLogger("QQBot.EventRouter")

class EventRouter:
    def __init__(self, bot):
        self.bot = bot

    async def dispatch(self, data: Dict[str, Any]):
        """事件分发器"""
        # 1. 优先处理 API 响应
        if "echo" in data:
            self.bot.qq_client.handle_response(data)
            return

        # 2. 处理主动上报事件
        post_type = data.get("post_type")
        if post_type == "message":
            await self.bot.message_handler.handle_message(data)
        elif post_type == "request":
            await self.bot.group_handler.handle_request(data)
        elif post_type == "notice":
            await self.bot.group_handler.handle_notice(data)
