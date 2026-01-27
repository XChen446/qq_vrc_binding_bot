"""
群组命令处理器 (Command Handler)
处理群聊相关的设置指令，如 !set
"""

import logging
import time
from typing import Dict, Any, List, Optional
from src.core.database.utils import safe_db_operation
from src.utils.admin_utils import is_group_admin_or_owner, is_super_admin

logger = logging.getLogger("QQBot.CommandHandler")


class CommandHandler:
    def __init__(self, bot):
        self.bot = bot

    async def handle_set_command(self, args: List[str], context: Dict[str, Any]) -> str:
        """
        处理 !set 命令
        用法: !set <setting_name> <value>
        仅在群聊中可用
        """
        user_id = context.get("user_id")
        group_id = context.get("group_id")

        # 检查是否在群聊中
        if not group_id:
            return "❌ 此命令仅可在群聊中使用"

        # 检查用户权限（必须是群管理员或超级管理员）
        is_admin = await is_group_admin_or_owner(user_id, group_id, self.bot.qq_client)
        is_super = is_super_admin(user_id, self.bot.global_config.admin_qq)

        if not (is_admin or is_super):
            return "❌ 仅群管理员或机器人超管可使用此命令"

        if len(args) < 2:
            return "用法: !set <设置名称> <设置值>\n例如: !set enable_welcome True"

        setting_name = args[0].lower()
        setting_value = " ".join(args[1:])

        # 根据设置名称处理不同的设置
        if setting_name == "enable_welcome":
            return await self._set_enable_welcome(group_id, setting_value)
        elif setting_name == "welcome_message":
            return await self._set_welcome_message(group_id, setting_value)
        elif setting_name == "auto_approve_group_request":
            return await self._set_auto_approve_group_request(group_id, setting_value)
        elif setting_name == "auto_bind_on_join":
            return await self._set_auto_bind_on_join(group_id, setting_value)
        else:
            return f"❌ 未知的设置项: {setting_name}\n支持的设置项: enable_welcome, welcome_message, auto_approve_group_request, auto_bind_on_join"

    async def _set_enable_welcome(self, group_id: int, value: str) -> str:
        """设置是否启用入群欢迎"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "enable_welcome", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                return f"✅ 已{status}入群欢迎功能"
            else:
                return "❌ 设置失败"
        except Exception as e:
            logger.error(f"设置入群欢迎功能失败: {e}")
            return "❌ 设置失败"

    async def _set_welcome_message(self, group_id: int, value: str) -> str:
        """设置欢迎消息内容"""
        try:
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "welcome_message", 
                value
            )
            
            if success:
                return f"✅ 已设置欢迎消息: {value}"
            else:
                return "❌ 设置失败"
        except Exception as e:
            logger.error(f"设置欢迎消息失败: {e}")
            return "❌ 设置失败"

    async def _set_auto_approve_group_request(self, group_id: int, value: str) -> str:
        """设置是否自动同意群请求"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "auto_approve_group_request", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                return f"✅ 已{status}自动同意群请求功能"
            else:
                return "❌ 设置失败"
        except Exception as e:
            logger.error(f"设置自动同意群请求功能失败: {e}")
            return "❌ 设置失败"

    async def _set_auto_bind_on_join(self, group_id: int, value: str) -> str:
        """设置是否自动绑定新加入的用户"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "auto_bind_on_join", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                return f"✅ 已{status}自动绑定新用户功能"
            else:
                return "❌ 设置失败"
        except Exception as e:
            logger.error(f"设置自动绑定新用户功能失败: {e}")
            return "❌ 设置失败"

    async def get_group_setting(self, group_id: int, setting_name: str, default_value: str = "") -> str:
        """获取群组特定设置"""
        try:
            setting_value = await safe_db_operation(
                self.bot.db.get_group_setting,
                group_id,
                setting_name
            )
            
            if setting_value is not None:
                return setting_value
            else:
                return default_value
        except Exception as e:
            logger.error(f"获取群组设置失败: {e}")
            return default_value