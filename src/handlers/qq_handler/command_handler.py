"""
群组命令处理器 (Command Handler)
处理群聊相关的设置指令，如 !set
"""

import logging
import time
from typing import Dict, Any, List, Optional
from src.core.database.utils import safe_db_operation
from src.utils.admin_utils import is_group_admin_or_owner, is_super_admin
from src.core.message_config import MessageConfig

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
            return self.bot.message_config.format_message('errors', 'not_in_group')

        # 检查用户权限（必须是群管理员或超级管理员）
        is_admin = await is_group_admin_or_owner(user_id, group_id, self.bot.qq_client)
        is_super = is_super_admin(user_id, self.bot.global_config.admin_qq)

        if not (is_admin or is_super):
            return self.bot.message_config.format_message('errors', 'admin_only')

        if len(args) < 2:
            return self.bot.message_config.get_message('help', 'usage_example')

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
        elif setting_name == "auto_reject_on_join":
            return await self._set_auto_reject_on_join(group_id, setting_value)
        elif setting_name == "verification_mode":
            return await self._set_verification_mode(group_id, setting_value)
        elif setting_name == "vrc_group_id":
            return await self._set_vrc_group_id(group_id, setting_value)
        elif setting_name == "target_role_id":
            return await self._set_target_role_id(group_id, setting_value)
        elif setting_name == "auto_assign_role":
            return await self._set_auto_assign_role(group_id, setting_value)
        elif setting_name == "auto_rename":
            return await self._set_auto_rename(group_id, setting_value)
        elif setting_name == "check_group_membership":
            return await self._set_check_group_membership(group_id, setting_value)
        elif setting_name == "check_troll":
            return await self._set_check_troll(group_id, setting_value)
        else:
            return f"❌ 未知的设置项: {setting_name}\n支持的设置项:\n  基础设置: enable_welcome, welcome_message, auto_approve_group_request, auto_bind_on_join\n  验证设置: auto_reject_on_join, verification_mode, vrc_group_id, target_role_id, auto_assign_role, auto_rename, check_group_membership, check_troll"

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
                setting_name = self.bot.message_config.get_message('settings', 'enable_welcome_desc')
                return self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置入群欢迎功能失败 [Group: {group_id}, Value: {enabled}]: {e}", exc_info=True)
            return self.bot.message_config.get_message('errors', 'setting_failed')

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
                return self.bot.message_config.format_message('success', 'setting_value_updated', setting_name='欢迎消息', value=value)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置欢迎消息失败 [Group: {group_id}, Value: {value}]: {e}", exc_info=True)
            return self.bot.message_config.get_message('errors', 'setting_failed')

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
                setting_name = self.bot.message_config.get_message('settings', 'auto_approve_group_request_desc')
                return self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置自动同意群请求功能失败 [Group: {group_id}, Value: {enabled}]: {e}", exc_info=True)
            return self.bot.message_config.get_message('errors', 'setting_failed')

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
                setting_name = self.bot.message_config.get_message('settings', 'auto_bind_on_join_desc')
                return self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置自动绑定新用户功能失败 [Group: {group_id}, Value: {enabled}]: {e}", exc_info=True)
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_auto_reject_on_join(self, group_id: int, value: str) -> str:
        """设置是否启用自动拒绝"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "auto_reject_on_join", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                setting_name = self.bot.message_config.get_message('settings', 'auto_reject_on_join_desc')
                return self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置自动拒绝功能失败 [Group: {group_id}, Value: {enabled}]: {e}", exc_info=True)
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_verification_mode(self, group_id: int, value: str) -> str:
        """设置验证模式"""
        try:
            # 验证模式值
            valid_modes = ['mixed', 'strict', 'disabled']
            if value.lower() not in valid_modes:
                return self.bot.message_config.format_message('errors', 'invalid_verification_mode', mode=value, valid_modes=', '.join(valid_modes))
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "verification_mode", 
                value.lower()
            )
            
            if success:
                setting_name = self.bot.message_config.get_message('settings', 'verification_mode_desc')
                return self.bot.message_config.format_message('success', 'setting_value_updated', setting_name=setting_name, value=value.lower())
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置验证模式失败 [Group: {group_id}, Value: {value}]: {e}", exc_info=True)
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_vrc_group_id(self, group_id: int, value: str) -> str:
        """设置VRChat群组ID"""
        try:
            # 验证VRChat群组ID格式
            if not value.strip():
                return self.bot.message_config.get_message('errors', 'vrc_group_id_required')
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "vrc_group_id", 
                value
            )
            
            if success:
                result_msg = self.bot.message_config.format_message('success', 'vrc_group_id_set', vrc_group_id=value)
                
                # 检查是否启用了自动分配角色，提醒用户需要相应权限
                auto_assign_role_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "auto_assign_role", "False")
                if auto_assign_role_setting.lower() == "true":
                    result_msg += "\n" + self.bot.message_config.get_message('reminders', 'permission_needed_for_role_assignment')
                
                return result_msg
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置VRChat群组ID失败: {e}")
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_target_role_id(self, group_id: int, value: str) -> str:
        """设置目标角色ID"""
        try:
            # 验证角色ID格式
            if not value.strip():
                return self.bot.message_config.get_message('errors', 'target_role_id_required')
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "target_role_id", 
                value
            )
            
            if success:
                result_msg = self.bot.message_config.format_message('success', 'target_role_id_set', target_role_id=value)
                
                # 检查是否启用了自动分配角色，提醒用户需要相应权限
                auto_assign_role_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "auto_assign_role", "False")
                if auto_assign_role_setting.lower() == "true":
                    result_msg += "\n" + self.bot.message_config.get_message('reminders', 'permission_needed_for_specific_role')
                    
                    # 检查是否已设置群组ID
                    vrc_group_id = await safe_db_operation(self.bot.db.get_group_setting, group_id, "vrc_group_id", "")
                    if not vrc_group_id:
                        result_msg += "\n" + self.bot.message_config.get_message('reminders', 'vrc_group_id_needed')
                
                return result_msg
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置目标角色ID失败: {e}")
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_auto_assign_role(self, group_id: int, value: str) -> str:
        """设置是否自动分配角色"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "auto_assign_role", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                setting_name = self.bot.message_config.get_message('settings', 'auto_assign_role_desc')
                result_msg = self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
                
                if enabled:
                    # 检查是否已设置群组ID和角色ID
                    vrc_group_id = await safe_db_operation(self.bot.db.get_group_setting, group_id, "vrc_group_id", "")
                    target_role_id = await safe_db_operation(self.bot.db.get_group_setting, group_id, "target_role_id", "")
                    
                    if not vrc_group_id or not target_role_id:
                        result_msg += "\n" + self.bot.message_config.get_message('reminders', 'vrc_group_id_needed')
                        result_msg += "\n" + self.bot.message_config.get_message('reminders', 'setup_instructions')
                        result_msg += "\n" + self.bot.message_config.get_message('reminders', 'robot_permissions')
                
                return result_msg
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置自动分配角色功能失败: {e}")
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_auto_rename(self, group_id: int, value: str) -> str:
        """设置是否自动重命名"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "auto_rename", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                setting_name = self.bot.message_config.get_message('settings', 'auto_rename_desc')
                return self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置自动重命名功能失败: {e}")
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_check_group_membership(self, group_id: int, value: str) -> str:
        """设置是否检查群组成员资格"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "check_group_membership", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                setting_name = self.bot.message_config.get_message('settings', 'check_group_membership_desc')
                return self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置群组成员资格检查功能失败: {e}")
            return self.bot.message_config.get_message('errors', 'setting_failed')

    async def _set_check_troll(self, group_id: int, value: str) -> str:
        """设置是否检查风险账号"""
        try:
            # 解析布尔值
            enabled = value.lower() in ['true', '1', 'yes', 'on', '启用', '开启']
            
            # 存储到数据库
            success = await safe_db_operation(
                self.bot.db.set_group_setting, 
                group_id, 
                "check_troll", 
                str(enabled)
            )
            
            if success:
                status = "启用" if enabled else "禁用"
                setting_name = self.bot.message_config.get_message('settings', 'check_troll_desc')
                return self.bot.message_config.format_message('success', 'setting_updated', status=status, setting_name=setting_name)
            else:
                return self.bot.message_config.get_message('errors', 'setting_failed')
        except Exception as e:
            logger.error(f"设置风险账号检查功能失败: {e}")
            return self.bot.message_config.get_message('errors', 'setting_failed')

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