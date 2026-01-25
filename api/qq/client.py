import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("QQBot.API")

class QQClient:
    def __init__(self, websocket_manager):
        self.ws_manager = websocket_manager
        self._echo_map: Dict[str, asyncio.Future] = {}

    async def _call_api(self, action: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """封装 OneBot API 调用逻辑"""
        if not self.ws_manager.ws:
            logger.error("WebSocket 未连接，无法调用 API")
            return {}
            
        echo = f"echo_{time.time()}"
        future = asyncio.get_event_loop().create_future()
        self._echo_map[echo] = future
        
        await self.ws_manager.ws.send(json.dumps({
            "action": action,
            "params": params,
            "echo": echo
        }))
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"API 调用超时: {action}")
            return {}
        finally:
            self._echo_map.pop(echo, None)

    def handle_response(self, data: Dict[str, Any]):
        """处理 API 响应数据"""
        echo = data.get("echo")
        if echo and echo in self._echo_map:
            self._echo_map[echo].set_result(data)

    async def send_group_msg(self, group_id: int, message: str):
        return await self._call_api("send_group_msg", {"group_id": group_id, "message": message})

    async def send_private_msg(self, user_id: int, message: str):
        return await self._call_api("send_private_msg", {"user_id": user_id, "message": message})

    async def approve_request(self, flag: str, sub_type: str = "add") -> bool:
        res = await self._call_api("set_group_add_request", {
            "flag": str(flag),
            "sub_type": sub_type,
            "approve": True
        }, timeout=10)
        return res.get("status") == "ok"

    async def reject_request(self, flag: str, sub_type: str, reason: str):
        res = await self._call_api("set_group_add_request", {
            "flag": str(flag),
            "sub_type": sub_type,
            "approve": False,
            "reason": reason
        }, timeout=10)
        return res.get("status") == "ok"

    async def set_group_card(self, group_id: int, user_id: int, card: str):
        return await self._call_api("set_group_card", {"group_id": group_id, "user_id": user_id, "card": card})

    async def get_group_member_list(self, group_id: int) -> List[Dict[str, Any]]:
        res = await self._call_api("get_group_member_list", {"group_id": group_id})
        return res.get("data", []) if res.get("status") == "ok" else []

    async def get_stranger_info(self, user_id: int) -> Dict[str, Any]:
        res = await self._call_api("get_stranger_info", {"user_id": user_id})
        return res.get("data", {}) if res.get("status") == "ok" else {}
