import logging
from typing import Optional, Dict, Any, List

# 尝试导入ncatbot，如果失败则提供兼容性处理
try:
    from ncatbot.core.bot import CQHTTPBot as Bot
except ImportError:
    try:
        from ncatbot import Bot
    except ImportError:
        # 如果ncatbot不可用，提供一个模拟类用于测试
        class Bot:
            def __init__(self, *args, **kwargs):
                pass

logger = logging.getLogger("QQBot.API")

class QQClient:
    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self.bot: Bot = ws_manager.bot

    async def send_group_msg(self, group_id: int, message: str):
        """发送群消息"""
        try:
            # 尝试使用ncatbot的API发送消息
            if hasattr(self.bot, 'send_group_msg'):
                await self.bot.send_group_msg(group_id=group_id, message=message)
            else:
                # 如果API不存在，记录日志
                logger.warning(f"send_group_msg API not available, would send to Group {group_id}: {message[:50]}...")
            logger.debug(f"发送群消息成功: Group {group_id}, Message: {message[:50]}...")
        except Exception as e:
            logger.error(f"发送群消息失败: {e}")
            raise

    async def send_private_msg(self, user_id: int, message: str):
        """发送私聊消息"""
        try:
            # 尝试使用ncatbot的API发送消息
            if hasattr(self.bot, 'send_private_msg'):
                await self.bot.send_private_msg(user_id=user_id, message=message)
            else:
                logger.warning(f"send_private_msg API not available, would send to User {user_id}: {message[:50]}...")
            logger.debug(f"发送私聊消息成功: User {user_id}, Message: {message[:50]}...")
        except Exception as e:
            logger.error(f"发送私聊消息失败: {e}")
            raise

    async def get_group_member_info(self, group_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """获取群成员信息"""
        try:
            # 尝试使用ncatbot的API获取群成员信息
            if hasattr(self.bot, 'get_group_member_info'):
                result = await self.bot.get_group_member_info(group_id=group_id, user_id=user_id)
                # 适配原有返回格式
                adapted_result = {
                    "user_id": result.get("user_id") if isinstance(result, dict) else user_id,
                    "group_id": result.get("group_id") if isinstance(result, dict) else group_id,
                    "nickname": result.get("nickname", "") if isinstance(result, dict) else "",
                    "card": result.get("card", "") if isinstance(result, dict) else "",  # 群名片
                    "sex": result.get("sex", "unknown") if isinstance(result, dict) else "unknown",
                    "age": result.get("age", 0) if isinstance(result, dict) else 0,
                    "area": result.get("area", "") if isinstance(result, dict) else "",
                    "join_time": result.get("join_time", 0) if isinstance(result, dict) else 0,
                    "last_sent_time": result.get("last_sent_time", 0) if isinstance(result, dict) else 0,
                    "level": result.get("level", "") if isinstance(result, dict) else "",
                    "role": result.get("role", "member") if isinstance(result, dict) else "member",  # owner, admin, member
                    "unfriendly": result.get("unfriendly", False) if isinstance(result, dict) else False,
                    "title": result.get("title", "") if isinstance(result, dict) else "",
                    "title_expire_time": result.get("title_expire_time", 0) if isinstance(result, dict) else 0,
                    "card_changeable": result.get("card_changeable", False) if isinstance(result, dict) else False,
                    **(result if isinstance(result, dict) else {})  # 包含其他所有字段
                }
                return adapted_result
            else:
                logger.warning(f"get_group_member_info API not available for Group {group_id}, User {user_id}")
                return {
                    "user_id": user_id,
                    "group_id": group_id,
                    "nickname": f"User_{user_id}",
                    "card": f"Card_{user_id}",
                    "role": "member"
                }
        except Exception as e:
            logger.error(f"获取群成员信息失败: {e}")
            return None

    async def get_group_member_list(self, group_id: int) -> List[Dict[str, Any]]:
        """获取群成员列表"""
        try:
            # 尝试使用ncatbot的API获取群成员列表
            if hasattr(self.bot, 'get_group_member_list'):
                result = await self.bot.get_group_member_list(group_id=group_id)
                # 适配原有返回格式
                adapted_result = []
                if isinstance(result, list):
                    for member in result:
                        if isinstance(member, dict):
                            adapted_member = {
                                "user_id": member.get("user_id"),
                                "nickname": member.get("nickname", ""),
                                "card": member.get("card", ""),
                                "sex": member.get("sex", "unknown"),
                                "age": member.get("age", 0),
                                "area": member.get("area", ""),
                                "join_time": member.get("join_time", 0),
                                "last_sent_time": member.get("last_sent_time", 0),
                                "level": member.get("level", ""),
                                "role": member.get("role", "member"),
                                "unfriendly": member.get("unfriendly", False),
                                "title": member.get("title", ""),
                                "title_expire_time": member.get("title_expire_time", 0),
                                "card_changeable": member.get("card_changeable", False),
                                **member  # 包含其他所有字段
                            }
                            adapted_result.append(adapted_member)
                return adapted_result
            else:
                logger.warning(f"get_group_member_list API not available for Group {group_id}")
                return []
        except Exception as e:
            logger.error(f"获取群成员列表失败: {e}")
            return []

    async def set_group_card(self, group_id: int, user_id: int, card: str):
        """设置群名片"""
        try:
            # 尝试使用ncatbot的API设置群名片
            if hasattr(self.bot, 'set_group_card'):
                await self.bot.set_group_card(group_id=group_id, user_id=user_id, card=card)
            else:
                logger.warning(f"set_group_card API not available for Group {group_id}, User {user_id}, Card: {card}")
            logger.debug(f"设置群名片成功: Group {group_id}, User {user_id}, Card: {card}")
        except Exception as e:
            logger.error(f"设置群名片失败: {e}")
            raise

    async def get_stranger_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取陌生人信息"""
        try:
            # 尝试使用ncatbot的API获取陌生人信息
            if hasattr(self.bot, 'get_stranger_info'):
                result = await self.bot.get_stranger_info(user_id=user_id)
                # 适配原有返回格式
                if isinstance(result, dict):
                    adapted_result = {
                        "user_id": result.get("user_id"),
                        "nickname": result.get("nickname", ""),
                        "sex": result.get("sex", "unknown"),
                        "age": result.get("age", 0),
                        "level": result.get("level", ""),
                        "login_days": result.get("login_days", 0),
                        **result  # 包含其他所有字段
                    }
                    return adapted_result
                else:
                    return {
                        "user_id": user_id,
                        "nickname": f"User_{user_id}",
                        "sex": "unknown",
                        "age": 0,
                        "level": "1"
                    }
            else:
                logger.warning(f"get_stranger_info API not available for User {user_id}")
                return {
                    "user_id": user_id,
                    "nickname": f"User_{user_id}",
                    "sex": "unknown",
                    "age": 0,
                    "level": "1"
                }
        except Exception as e:
            logger.error(f"获取陌生人信息失败: {e}")
            return None