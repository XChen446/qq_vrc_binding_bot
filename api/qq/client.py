import time
import asyncio
import logging
from typing import Dict, Any, List

logger = logging.getLogger("QQBot.API")


def _is_success(response: Dict[str, Any]) -> bool:
    """检查 API 调用是否成功"""
    return response.get("status") == "ok"


class QQClient:
    def __init__(self, websocket_manager):
        self.ws_manager = websocket_manager
        self._echo_map: Dict[str, asyncio.Future] = {}

    async def _call_api(self, action: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """封装 OneBot API 调用逻辑"""
        if not self.ws_manager.ws:
            logger.error(f"WebSocket 未连接，无法调用 API: {action}")
            return {}
            
        echo = f"echo_{time.time()}_{action}"
        future = asyncio.get_event_loop().create_future()
        self._echo_map[echo] = future
        
        try:
            logger.debug(f"调用 API: {action} | Params: {params}")
            await self.ws_manager.send({
                "action": action,
                "params": params,
                "echo": echo
            })
            
            result = await asyncio.wait_for(future, timeout=timeout)
            logger.debug(f"API 响应 ({action}): Status={result.get('status')} | RetCode={result.get('retcode')}")
            return result
        except asyncio.TimeoutError:
            logger.warning(f"API 调用超时: {action}")
            return {}
        except Exception as e:
            logger.error(f"API 调用异常 ({action}): {e}")
            return {}
        finally:
            if echo in self._echo_map:
                del self._echo_map[echo]

    def handle_response(self, data: Dict[str, Any]):
        """处理 API 响应数据"""
        echo = data.get("echo")
        if echo and echo in self._echo_map:
            if not self._echo_map[echo].done():
                self._echo_map[echo].set_result(data)

    # ==================== 消息发送接口 ====================

    async def send_group_msg(self, group_id: int, message: str) -> Dict[str, Any]:
        """发送群消息"""
        return await self._call_api("send_group_msg", {
            "group_id": group_id, 
            "message": message
        })

    async def send_private_msg(self, user_id: int, message: str) -> Dict[str, Any]:
        """发送私聊消息"""
        return await self._call_api("send_private_msg", {
            "user_id": user_id, 
            "message": message
        })

    # ==================== 请求处理接口 ====================

    async def approve_request(self, flag: str, sub_type: str = "add") -> bool:
        """同意加群/加好友请求"""
        res = await self._call_api("set_group_add_request", {
            "flag": str(flag),
            "sub_type": sub_type,
            "approve": True
        }, timeout=10)
        return _is_success(res)

    async def reject_request(self, flag: str, sub_type: str, reason: str = "") -> bool:
        """拒绝加群/加好友请求"""
        res = await self._call_api("set_group_add_request", {
            "flag": str(flag),
            "sub_type": sub_type,
            "approve": False,
            "reason": reason
        }, timeout=10)
        return _is_success(res)

    # ==================== 群组管理接口 ====================

    async def set_group_card(self, group_id: int, user_id: int, card: str) -> bool:
        """设置群名片"""
        res = await self._call_api("set_group_card", {
            "group_id": group_id, 
            "user_id": user_id, 
            "card": card
        })
        return _is_success(res)

    async def get_group_member_list(self, group_id: int) -> List[Dict[str, Any]]:
        """获取群成员列表"""
        res = await self._call_api("get_group_member_list", {"group_id": group_id})
        return res.get("data", []) if _is_success(res) else []

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = False) -> Dict[str, Any]:
        """获取群成员信息"""
        res = await self._call_api("get_group_member_info", {
            "group_id": group_id, 
            "user_id": user_id, 
            "no_cache": no_cache
        })
        return res.get("data", {}) if _is_success(res) else {}

    # ==================== 用户信息接口 ====================

    async def get_stranger_info(self, user_id: int) -> Dict[str, Any]:
        """获取陌生人信息"""
        res = await self._call_api("get_stranger_info", {"user_id": user_id})
        return res.get("data", {}) if _is_success(res) else {}
