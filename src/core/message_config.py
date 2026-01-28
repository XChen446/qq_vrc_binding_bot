import yaml
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("MessageConfig")

class MessageConfig:
    """
    消息配置管理器
    负责加载和管理消息模板配置
    """
    
    def __init__(self, config_path: str = "config/message.yml"):
        """
        初始化消息配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 "config/message.yml"
        """
        self.config_path = config_path
        self.messages = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """
        加载消息配置文件
        
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            # 检查配置文件是否存在
            if not os.path.exists(self.config_path):
                logger.warning(f"消息配置文件不存在: {self.config_path}")
                # 尝试创建默认配置
                self.create_default_config()
                return False
            
            # 读取YAML配置文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.messages = yaml.safe_load(f)
            
            logger.info(f"消息配置已加载: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"加载消息配置失败: {e}")
            return False
    
    def create_default_config(self):
        """
        创建默认消息配置文件
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # 默认消息配置
            default_messages = {
                "errors": {
                    "group_only": "❌ 该指令仅限在群聊中使用喵~",
                    "admin_only": "❌ 仅群管理员或机器人超管可使用此命令",
                    "super_admin_only": "❌ 仅机器人超管可使用此命令",
                    "not_in_group": "❌ 此命令仅可在群聊中使用",
                    "setting_failed": "❌ 设置失败",
                    "database_operation_failed": "❌ 数据库操作失败",
                    "invalid_format": "❌ 格式不正确",
                    "user_not_found": "❌ 无法获取用户信息",
                    "search_failed": "❌ 搜索失败: {error}",
                    "query_failed": "❌ 查询失败: {error}",
                    "bind_failed": "❌ 绑定失败: {error}",
                    "unbind_failed": "❌ 解绑失败: {error}",
                    "verify_failed": "❌ 验证失败",
                    "verification_expired": "❌ 验证码已过期，请使用!code重新获取。",
                    "no_verification_request": "❌ 您当前没有待验证的请求。请先使用 !bind [VRChat名字] 申请绑定，或联系管理员。",
                    "unable_to_get_vrc_info": "❌ 无法获取您的VRChat信息，请重新申请绑定。",
                    "generate_code_failed": "❌ 生成验证码失败，请稍后重试。",
                    "image_generation_failed": "❌ 生成图片失败: {error}",
                    "user_not_in_group": "❌ 无法绑定：QQ号 {qq_id} 不在本群中",
                    "vrc_group_id_required": "❌ VRChat群组ID不能为空",
                    "target_role_id_required": "❌ 目标角色ID不能为空",
                    "invalid_verification_mode": "❌ 无效的验证模式: {mode}. 支持的模式: {valid_modes}",
                    "already_bound_vrc_group": "❌ 绑定失败！本群已绑定了 VRChat 群组！请联系机器人管理员！"
                },
                "success": {
                    "bind_success": "✅ 绑定成功！VRChat 账号: {vrc_name}",
                    "verification_success": "✅ 验证成功！已绑定 VRChat 账号: {vrc_name}",
                    "unbind_success": "✅ 已从本群解绑 QQ: {qq_id}",
                    "global_unbind_success": "✅ 已全局解绑 QQ: {qq_id}",
                    "global_bind_success": "✅ 已全局绑定 QQ {qq_id} 到 VRChat: {vrc_name}",
                    "setting_updated": "✅ 已{status}{setting_name}功能",
                    "setting_value_updated": "✅ 已设置{setting_name}: {value}",
                    "vrc_group_id_set": "✅ 已设置VRChat群组ID为: {vrc_group_id}",
                    "target_role_id_set": "✅ 已设置目标角色ID为: {target_role_id}",
                    "role_assigned": "✅ 角色分配成功",
                    "list_generated": "✅ 列表已生成",
                    "verification_code_generated": "您的验证码是: {code}\n有效时间剩余: {remaining}s\n请将 VRChat 状态描述修改为此验证码，然后发送 !verify\n目标VRChat账号: {vrc_name}"
                },
                "verification": {
                    "welcome_message": "欢迎！",
                    "verification_request_template": "[CQ:at,qq={user_id}] 欢迎加入！\n检测到您申请绑定的 VRChat 账号为: {vrc_name}\n为了验证身份，请将您的 VRChat 状态描述(Status Description)修改为以下数字：\n{code}\n修改完成后，请在群内发送 !verify 完成验证。",
                    "verification_failed": "❌ 验证失败。\n要求状态描述包含: {code}\n当前状态描述: {status_desc}\n请修改后再次输入 !verify",
                    "already_bound": "✅ 您已绑定 VRChat 账号 ({vrc_display_name})。",
                    "already_bound_verify": "✅ 您已绑定 VRChat 账号 ({vrc_display_name})，无需再次验证。",
                    "code_regenerated": "验证码已重新生成，请检查您的VRChat状态描述要求。",
                    "verification_timeout": "验证超时，请重新申请。",
                    "verification_progress": "您正在进行验证，请稍候..."
                },
                "help": {
                    "title": "VRChat 机器人指令列表:",
                    "commands": {
                        "instances": "查看群组活跃实例",
                        "bind": "[QQ] [VRC ID/名字] 手动登记账号",
                        "unbind": "[QQ] - 解绑指定QQ登记",
                        "list": "[QQ群号] or [global] - 查看指定群或全局的绑定记录",
                        "query": "[名字/ID] 查询登记记录",
                        "search": "[名字/ID] 搜索VRChat用户",
                        "me": "查看我的登记信息",
                        "verify": "验证VRChat账号归属",
                        "unbound": "查询本群未登记成员",
                        "code": "重新获取验证码",
                        "admin": "[@某人]-管理群管理员",
                        "glbind": "[QQ] [VRC ID/名字]-全局绑定账号",
                        "unglbind": "[QQ]-全局解绑账号",
                        "set": "[设置项] [值] - 设置群组功能开关和参数(仅群管可用)"
                    },
                    "usage_example": "用法: !set <设置名称> <设置值>\n例如: !set enable_welcome True",
                    "verification_modes": {
                        "title": "💡 验证模式说明:",
                        "mixed": "mixed - 混合模式: 允许用户入群后完成验证，超时未验证将被禁言",
                        "strict": "strict - 严格模式: 必须先验证才能入群，超时未验证将被踢出",
                        "disabled": "disabled - 禁用模式: 不强制验证"
                    },
                    "permissions_note": {
                        "title": "🛡️ 重要提醒:",
                        "content": "当启用 auto_assign_role 时，需要确保机器人账号\n在 VRChat 群组中有分配角色的权限。\n请使用 !set vrc_group_id 和 !set target_role_id 设置必要参数。"
                    },
                    "set_hint": "💡 使用 !set 可设置群组功能",
                    "help_command": "!help - 显示此帮助信息"
                },
                "search": {
                    "no_results": "❌ 未找到用户: {query}",
                    "results_header": "找到 {count} 个用户:",
                    "result_item": "{display_name} ({user_id}) - {status}",
                    "too_many_results": "... 还有 {more_count} 人",
                    "query_no_results": "❌ 未找到绑定记录: {query}",
                    "query_results_header": "找到 {count} 条绑定记录:",
                    "query_result_item": "QQ: {qq_id} -> VRChat: {vrc_name} (来自群: {origin_group})"
                },
                "lists": {
                    "no_bindings": "本群尚无已绑定的用户",
                    "no_global_bindings": "目前没有已绑定的用户",
                    "no_unbound_members": "✅ 该群所有成员均已绑定 VRChat 账号",
                    "unbound_members_header": "群 {group_id} 中未绑定 VRChat 的成员:",
                    "unbound_members_truncated": "... 还有 {count} 人",
                    "global_list_only_for_admin": "❌ 仅超级管理员可以查看全局列表"
                },
                "profile": {
                    "not_bound": "❌ 您还未绑定 VRChat 账号",
                    "profile_header": "您的绑定信息:",
                    "profile_detail": "VRChat: {vrc_name} ({vrc_id})\n绑定时间: {bind_time}\n绑定来源群: {origin_group}"
                },
                "settings": {
                    "enable_welcome_desc": "入群欢迎功能",
                    "auto_approve_group_request_desc": "自动同意群请求功能",
                    "auto_bind_on_join_desc": "自动绑定新用户功能",
                    "auto_reject_on_join_desc": "自动拒绝功能",
                    "verification_mode_desc": "验证模式",
                    "auto_assign_role_desc": "自动分配角色功能",
                    "auto_rename_desc": "自动重命名功能",
                    "check_group_membership_desc": "群组成员资格检查功能",
                    "check_troll_desc": "风险账号检查功能",
                    "welcome_message_desc": "欢迎消息内容",
                    "vrc_group_id_desc": "VRChat群组ID",
                    "target_role_id_desc": "目标角色ID"
                },
                "reminders": {
                    "permission_needed_for_role_assignment": "🛡️ 重要提醒：请确保机器人账号拥有在该 VRChat 群组中分配角色的权限！",
                    "permission_needed_for_specific_role": "🛡️ 重要提醒：请确保机器人账号拥有在 VRChat 群组中分配此角色的权限！",
                    "vrc_group_id_needed": "⚠️ 注意：请确保已设置 VRChat 群组 ID (!set vrc_group_id)，否则自动分配角色功能将无法工作。",
                    "setup_instructions": "🔧 请使用 !set vrc_group_id [群组ID] 和 !set target_role_id [角色ID] 进行设置。",
                    "robot_permissions": "🛡️ 重要：请确保机器人账号拥有在 VRChat 群组中分配角色的权限。"
                },
                "welcome": {
                    "default": "欢迎！请绑定 VRChat 账号。",
                    "bound_user": "欢迎回来，{display_name}！",
                    "new_user": "欢迎新朋友 {display_name}！请绑定您的VRChat账号。"
                },
                "system": {
                    "cooldown_message": "指令正在冷却中，请稍后再试。",
                    "command_disabled": "此指令当前已禁用。",
                    "unknown_command": "未知指令，发送 !help 查看帮助。",
                    "access_denied": "访问被拒绝，权限不足。"
                }
            }
            
            # 写入YAML文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_messages, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info(f"默认消息配置已创建: {self.config_path}")
            
        except Exception as e:
            logger.error(f"创建默认消息配置失败: {e}")
    
    def get_message(self, *keys, default: str = "") -> str:
        """
        获取消息模板
        
        Args:
            *keys: 消息路径，例如 get_message('errors', 'group_only')
            default: 默认值，当找不到消息时返回
            
        Returns:
            str: 消息模板字符串，如果找不到则返回默认值（默认为空字符串）
        """
        current = self.messages
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                logger.warning(f"消息模板未找到: {'.'.join(keys)}")
                return default
        return current if isinstance(current, str) else default
    
    def format_message(self, *keys, **kwargs) -> str:
        """
        获取并格式化消息模板
        
        Args:
            *keys: 消息路径
            **kwargs: 用于格式化消息的参数
            
        Returns:
            str: 格式化后的消息字符串
        """
        template = self.get_message(*keys)
        if template:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                logger.warning(f"消息格式化失败，缺少参数: {e}, 模板: {template}")
                return template
        return ""
    
    def update_message(self, *keys, message: str):
        """
        更新消息模板
        
        Args:
            *keys: 消息路径
            message: 新的消息内容
        """
        current = self.messages
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = message
        logger.debug(f"消息模板已更新: {'.'.join(keys)}")
    
    def reload(self):
        """
        重新加载配置文件
        """
        self.load_config()