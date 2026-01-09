"""
群组处理器
处理QQ群相关事件：入群申请、入群、退群等
"""

import asyncio
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from ..api.async_vrchat_api import AsyncVRChatAPIClient
from ..core.async_qq_bot import AsyncQQBotManager
from ..core.data_manager import DataManager
from ..utils.message_template import MessageTemplate


class GroupHandler:
    """群组事件处理器"""
    
    def __init__(self, qq_bot: AsyncQQBotManager,
                 vrc_api: AsyncVRChatAPIClient,
                 data_manager: DataManager,
                 message_template: MessageTemplate,
                 groups_config: List[Dict]):
        """
        初始化群组处理器
        
        Args:
            qq_bot: QQ Bot管理器
            vrc_api: VRChat API客户端
            data_manager: 数据管理器
            message_template: 消息模板处理器
            groups_config: 群组配置列表
        """
        self.qq_bot = qq_bot
        self.vrc_api = vrc_api
        self.data_manager = data_manager
        self.message_template = message_template
        self.groups_config = {str(g['group_id']): g for g in groups_config}
        
        # 速率限制
        self.rate_limiter = {}
        self.rate_limit_window = 60  # 60秒窗口
        self.max_requests_per_window = 10  # 每窗口最大请求数
        
        logger.info(f"群组处理器初始化完成，管理 {len(groups_config)} 个群组")
    
    async def handle_group_request(self, event_data: Dict):
        """
        处理入群申请
        
        Args:
            event_data: 事件数据
        """
        try:
            # 提取事件信息
            group_id = event_data.get('group_id')
            user_id = event_data.get('user_id')
            comment = event_data.get('comment', '')
            flag = event_data.get('flag', '')
            
            # 检查是否是管理的群组
            group_config = self.groups_config.get(str(group_id))
            if not group_config or not group_config.get('enabled', False):
                logger.debug(f"群组 {group_id} 不在管理范围内")
                return
            
            logger.info(f"收到入群申请 [群{group_id}] [用户{user_id}]: {comment}")
            
            # 检查速率限制
            if not await self._check_rate_limit(user_id):
                logger.warning(f"用户 {user_id} 请求过于频繁")
                return
            
            # 提取VRChat用户ID
            vrc_user_id = self._extract_vrc_user_id(comment)
            
            if not vrc_user_id:
                # 格式不正确，发送提示并拒绝
                await self._handle_invalid_format(group_id, user_id, comment)
                return
            
            # 验证VRChat用户ID格式
            if not self.vrc_api.validate_user_id(vrc_user_id):
                await self._handle_invalid_format(group_id, user_id, comment)
                return
            
            # 检查用户是否已绑定
            existing_binding = self.data_manager.get_binding_by_qq(user_id)
            if existing_binding:
                logger.warning(f"用户 {user_id} 已绑定到VRChat用户")
                await self._handle_already_bound(group_id, user_id, existing_binding)
                return
            
            # 获取VRChat用户信息
            user_info = await self.vrc_api.get_user_info(vrc_user_id)
            if not user_info:
                await self._handle_user_not_found(group_id, user_id, vrc_user_id)
                return
            
            # 检查用户状态
            if user_info.get('state') == 'banned':
                await self._handle_user_banned(group_id, user_id, user_info)
                return
            
            vrc_username = user_info.get('displayName', vrc_user_id)
            
            # 尝试自动批准
            if group_config.get('auto_approve', True):
                success = await self._auto_approve_join_request(
                    group_id, user_id, vrc_user_id, vrc_username, 
                    group_config, flag
                )
                
                if success:
                    # 绑定用户
                    self.data_manager.bind_user(user_id, vrc_user_id, vrc_username)
                    
                    # 尝试添加到VRChat群组
                    await self._add_to_vrc_group(
                        group_config, vrc_user_id, vrc_username, user_id
                    )
                    
                    # 发送欢迎消息
                    await self._send_welcome_message(
                        group_id, user_id, vrc_user_id, vrc_username
                    )
                else:
                    # 通知管理员处理
                    await self._notify_admin(group_id, user_id, vrc_user_id, vrc_username)
            else:
                # 仅通知管理员，不自动处理
                await self._notify_admin(group_id, user_id, vrc_user_id, vrc_username)
                
        except Exception as e:
            logger.exception(f"处理入群申请时发生错误: {e}")
    
    async def handle_group_increase(self, event_data: Dict):
        """
        处理成员入群事件
        
        Args:
            event_data: 事件数据
        """
        try:
            group_id = event_data.get('group_id')
            user_id = event_data.get('user_id')
            operator_id = event_data.get('operator_id', 0)
            
            # 检查是否是管理的群组
            group_config = self.groups_config.get(str(group_id))
            if not group_config:
                return
            
            logger.info(f"成员入群 [群{group_id}] [用户{user_id}] 操作者: {operator_id}")
            
            # 获取用户绑定信息
            binding = self.data_manager.get_binding_by_qq(user_id)
            if binding:
                # 发送欢迎消息
                await self._send_welcome_message(
                    group_id, user_id, 
                    binding['vrc_user_id'], 
                    binding['vrc_username']
                )
            else:
                # 发送提示消息
                welcome_msg = "欢迎新成员！请使用 !bind <VRChat用户ID> 命令绑定您的VRChat账号。"
                await self.qq_bot.send_group_message(group_id, welcome_msg)
                
        except Exception as e:
            logger.exception(f"处理成员入群事件时发生错误: {e}")
    
    async def handle_group_decrease(self, event_data: Dict):
        """
        处理成员退群事件
        
        Args:
            event_data: 事件数据
        """
        try:
            group_id = event_data.get('group_id')
            user_id = event_data.get('user_id')
            operator_id = event_data.get('operator_id', 0)
            sub_type = event_data.get('sub_type', '')  # leave, kick
            
            # 检查是否是管理的群组
            group_config = self.groups_config.get(str(group_id))
            if not group_config:
                return
            
            logger.info(f"成员退群 [群{group_id}] [用户{user_id}] 类型: {sub_type}")
            
            # 获取用户绑定信息
            binding = self.data_manager.get_binding_by_qq(user_id)
            if binding:
                # 发送退群消息
                variables = self.message_template.create_leave_variables(
                    user_id, binding['vrc_user_id'], 
                    binding['vrc_username'], group_id
                )
                
                message = self.message_template.render('leave_message', variables)
                if message:
                    await self.qq_bot.send_group_message(group_id, message)
                
                # 如果是被踢出，从VRChat群组中移除
                if sub_type == 'kick' and group_config.get('auto_remove_on_kick', False):
                    await self._remove_from_vrc_group(
                        group_config, binding['vrc_user_id'], user_id
                    )
                
                # 删除绑定数据
                self.data_manager.unbind_user(user_id)
                
        except Exception as e:
            logger.exception(f"处理成员退群事件时发生错误: {e}")
    
    def _extract_vrc_user_id(self, comment: str) -> Optional[str]:
        """
        从入群申请备注中提取VRChat用户ID
        
        Args:
            comment: 申请备注
            
        Returns:
            VRChat用户ID或None
        """
        try:
            # 匹配VRChat用户ID格式
            pattern = r'usr_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            match = re.search(pattern, comment, re.IGNORECASE)
            
            if match:
                return match.group(0)
            else:
                return None
                
        except Exception as e:
            logger.exception(f"提取VRChat用户ID失败: {e}")
            return None
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """
        检查速率限制
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 未超出限制返回True
        """
        try:
            current_time = datetime.now()
            user_id_str = str(user_id)
            
            # 清理过期的记录
            self._cleanup_rate_limit_records()
            
            if user_id_str not in self.rate_limiter:
                self.rate_limiter[user_id_str] = []
            
            # 获取当前窗口内的请求
            window_start = current_time.timestamp() - self.rate_limit_window
            recent_requests = [
                req_time for req_time in self.rate_limiter[user_id_str]
                if req_time > window_start
            ]
            
            # 检查是否超出限制
            if len(recent_requests) >= self.max_requests_per_window:
                return False
            
            # 记录当前请求
            self.rate_limiter[user_id_str].append(current_time.timestamp())
            return True
            
        except Exception as e:
            logger.exception(f"检查速率限制失败: {e}")
            return True  # 出错时允许请求
    
    def _cleanup_rate_limit_records(self):
        """清理速率限制记录"""
        try:
            current_time = datetime.now().timestamp()
            cutoff_time = current_time - self.rate_limit_window
            
            for user_id in list(self.rate_limiter.keys()):
                self.rate_limiter[user_id] = [
                    req_time for req_time in self.rate_limiter[user_id]
                    if req_time > cutoff_time
                ]
                
                # 删除空记录
                if not self.rate_limiter[user_id]:
                    del self.rate_limiter[user_id]
                    
        except Exception as e:
            logger.exception(f"清理速率限制记录失败: {e}")
    
    async def _handle_invalid_format(self, group_id: int, user_id: int, comment: str):
        """
        处理格式不正确的入群申请
        
        Args:
            group_id: 群号
            user_id: 用户ID
            comment: 申请备注
        """
        try:
            # 拒绝入群申请
            await self.qq_bot.handle_group_request(group_id, user_id, comment, False)
            
            # 发送格式提示
            message = self.message_template.get_template('invalid_format')
            await self.qq_bot.send_private_message(user_id, message)
            
            logger.info(f"已拒绝格式不正确的入群申请 [群{group_id}] [用户{user_id}]")
            
        except Exception as e:
            logger.exception(f"处理格式错误时发生错误: {e}")
    
    async def _handle_already_bound(self, group_id: int, user_id: int, binding: Dict):
        """
        处理已绑定的用户
        
        Args:
            group_id: 群号
            user_id: 用户ID
            binding: 绑定信息
        """
        try:
            message = f"您已绑定VRChat账号: {binding['vrc_username']}"
            await self.qq_bot.send_private_message(user_id, message)
            
            logger.info(f"用户 {user_id} 尝试重复绑定")
            
        except Exception as e:
            logger.exception(f"处理已绑定用户时发生错误: {e}")
    
    async def _handle_user_not_found(self, group_id: int, user_id: int, vrc_user_id: str):
        """
        处理用户不存在的情况
        
        Args:
            group_id: 群号
            user_id: 用户ID
            vrc_user_id: VRChat用户ID
        """
        try:
            # 通知管理员
            admin_ids = self.groups_config[str(group_id)].get('admin_qq_ids', [])
            for admin_id in admin_ids:
                message = f"入群申请审查：用户 {user_id} 提供的VRChat ID不存在: {vrc_user_id}"
                await self.qq_bot.send_private_message(admin_id, message)
            
            logger.info(f"VRChat用户不存在: {vrc_user_id}")
            
        except Exception as e:
            logger.exception(f"处理用户不存在时发生错误: {e}")
    
    async def _handle_user_banned(self, group_id: int, user_id: int, user_info: Dict):
        """
        处理用户被封禁的情况
        
        Args:
            group_id: 群号
            user_id: 用户ID
            user_info: 用户信息
        """
        try:
            vrc_username = user_info.get('displayName', 'Unknown')
            
            # 拒绝入群申请
            await self.qq_bot.handle_group_request(group_id, user_id, '', False)
            
            # 通知管理员
            admin_ids = self.groups_config[str(group_id)].get('admin_qq_ids', [])
            for admin_id in admin_ids:
                variables = self.message_template.create_error_variables(
                    f"VRChat用户 {vrc_username} 已被封禁",
                    admin_id
                )
                message = self.message_template.render('user_banned', variables)
                await self.qq_bot.send_private_message(admin_id, message)
            
            logger.info(f"已拒绝被封禁用户: {vrc_username}")
            
        except Exception as e:
            logger.exception(f"处理被封禁用户时发生错误: {e}")
    
    async def _auto_approve_join_request(self, group_id: int, user_id: int,
                                        vrc_user_id: str, vrc_username: str,
                                        group_config: Dict, flag: str) -> bool:
        """
        自动批准入群申请
        
        Args:
            group_id: 群号
            user_id: 用户ID
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
            group_config: 群组配置
            flag: 申请标识
            
        Returns:
            bool: 批准成功返回True
        """
        try:
            # 批准入群申请
            success = await self.qq_bot.handle_group_request(
                group_id, user_id, flag, True
            )
            
            if success:
                logger.info(f"自动批准入群申请成功 [群{group_id}] [用户{user_id}]")
            else:
                logger.error(f"自动批准入群申请失败 [群{group_id}] [用户{user_id}]")
            
            return success
            
        except Exception as e:
            logger.exception(f"自动批准入群申请时发生错误: {e}")
            return False
    
    async def _add_to_vrc_group(self, group_config: Dict, 
                               vrc_user_id: str, vrc_username: str,
                               qq_id: int):
        """
        将用户添加到VRChat群组
        
        Args:
            group_config: 群组配置
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
            qq_id: QQ号
        """
        try:
            vrc_group_id = group_config.get('vrc_group_id')
            vrc_role_id = group_config.get('auto_assign_role')
            
            if not vrc_group_id or not vrc_role_id:
                logger.warning(f"未配置VRChat群组或角色ID")
                return
            
            # 添加到VRChat群组
            success, message = await self.vrc_api.add_user_to_group(
                vrc_group_id, vrc_user_id, vrc_role_id
            )
            
            if success:
                logger.success(f"用户 {qq_id} 已添加到VRChat群组 {vrc_group_id}")
            else:
                logger.error(f"添加用户到VRChat群组失败: {message}")
                
                # 发送失败通知
                group_id = group_config['group_id']
                admin_ids = group_config.get('admin_qq_ids', [])
                
                for admin_id in admin_ids:
                    variables = self.message_template.create_error_variables(
                        message, admin_id
                    )
                    error_msg = self.message_template.render(
                        'role_assignment_failed', variables
                    )
                    await self.qq_bot.send_private_message(admin_id, error_msg)
                    
        except Exception as e:
            logger.exception(f"添加用户到VRChat群组时发生错误: {e}")
    
    async def _remove_from_vrc_group(self, group_config: Dict, 
                                    vrc_user_id: str, qq_id: int):
        """
        从VRChat群组中移除用户
        
        Args:
            group_config: 群组配置
            vrc_user_id: VRChat用户ID
            qq_id: QQ号
        """
        try:
            vrc_group_id = group_config.get('vrc_group_id')
            
            if not vrc_group_id:
                return
            
            # 从VRChat群组中移除
            success, message = await self.vrc_api.remove_user_from_group(
                vrc_group_id, vrc_user_id
            )
            
            if success:
                logger.success(f"用户 {qq_id} 已从VRChat群组 {vrc_group_id} 移除")
            else:
                logger.error(f"从VRChat群组移除用户失败: {message}")
                
        except Exception as e:
            logger.exception(f"从VRChat群组移除用户时发生错误: {e}")
    
    async def _send_welcome_message(self, group_id: int, user_id: int,
                                   vrc_user_id: str, vrc_username: str):
        """
        发送欢迎消息
        
        Args:
            group_id: 群号
            user_id: 用户ID
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
        """
        try:
            # 创建变量
            variables = self.message_template.create_welcome_variables(
                user_id, vrc_user_id, vrc_username, group_id
            )
            
            # 渲染消息
            message = self.message_template.render('welcome_message', variables)
            
            if message:
                await self.qq_bot.send_group_message(group_id, message)
                logger.info(f"欢迎消息发送成功 [群{group_id}] [用户{user_id}]")
            
        except Exception as e:
            logger.exception(f"发送欢迎消息失败: {e}")
    
    async def _notify_admin(self, group_id: int, user_id: int,
                           vrc_user_id: str, vrc_username: str):
        """
        通知管理员处理
        
        Args:
            group_id: 群号
            user_id: 用户ID
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
        """
        try:
            admin_ids = self.groups_config[str(group_id)].get('admin_qq_ids', [])
            
            for admin_id in admin_ids:
                # 创建变量
                variables = self.message_template.create_manual_bind_variables(
                    user_id, vrc_user_id, vrc_username, admin_id
                )
                
                # 渲染消息
                message = self.message_template.render('review_request', variables)
                
                if message:
                    await self.qq_bot.send_private_message(admin_id, message)
            
            logger.info(f"已通知管理员处理 [群{group_id}] [用户{user_id}]")
            
        except Exception as e:
            logger.exception(f"通知管理员失败: {e}")
    
    async def handle_admin_command(self, event_data: Dict):
        """
        处理管理员命令
        
        Args:
            event_data: 事件数据
        """
        try:
            message = event_data.get('message', '')
            user_id = event_data.get('user_id')
            group_id = event_data.get('group_id')
            
            # 检查是否是管理员
            group_config = self.groups_config.get(str(group_id))
            if not group_config:
                return
            
            admin_ids = group_config.get('admin_qq_ids', [])
            if user_id not in admin_ids:
                return
            
            # 解析命令
            if message.startswith('!bind '):
                await self._handle_bind_command(event_data)
            elif message.startswith('!unbind '):
                await self._handle_unbind_command(event_data)
            elif message.startswith('!list'):
                await self._handle_list_command(event_data)
            elif message.startswith('!search '):
                await self._handle_search_command(event_data)
            elif message == '!help':
                await self._handle_help_command(event_data)
                
        except Exception as e:
            logger.exception(f"处理管理员命令时发生错误: {e}")
    
    async def _handle_bind_command(self, event_data: Dict):
        """处理绑定命令"""
        try:
            message = event_data.get('message', '')
            user_id = event_data.get('user_id')
            group_id = event_data.get('group_id')
            
            # 解析命令：!bind <qq_id> <vrc_user_id>
            parts = message.split()
            if len(parts) != 3:
                await self.qq_bot.send_group_message(group_id, "用法: !bind <QQ号> <VRChat用户ID>")
                return
            
            target_qq = int(parts[1])
            vrc_user_id = parts[2]
            
            # 验证VRChat用户ID格式
            if not self.vrc_api.validate_user_id(vrc_user_id):
                await self.qq_bot.send_group_message(group_id, "VRChat用户ID格式不正确")
                return
            
            # 获取VRChat用户信息
            user_info = await self.vrc_api.get_user_info(vrc_user_id)
            if not user_info:
                await self.qq_bot.send_group_message(group_id, "未找到该VRChat用户")
                return
            
            vrc_username = user_info.get('displayName', vrc_user_id)
            
            # 绑定用户
            success = self.data_manager.bind_user(target_qq, vrc_user_id, vrc_username, user_id)
            
            if success:
                # 发送成功消息
                variables = self.message_template.create_manual_bind_variables(
                    target_qq, vrc_user_id, vrc_username, user_id
                )
                message = self.message_template.render('manual_bind_success', variables)
                await self.qq_bot.send_group_message(group_id, message)
            else:
                await self.qq_bot.send_group_message(group_id, "绑定失败，用户可能已绑定")
                
        except Exception as e:
            logger.exception(f"处理绑定命令失败: {e}")
            await self.qq_bot.send_group_message(group_id, "绑定命令执行失败")
    
    async def _handle_unbind_command(self, event_data: Dict):
        """处理解绑命令"""
        try:
            message = event_data.get('message', '')
            user_id = event_data.get('user_id')
            group_id = event_data.get('group_id')
            
            # 解析命令：!unbind <qq_id>
            parts = message.split()
            if len(parts) != 2:
                await self.qq_bot.send_group_message(group_id, "用法: !unbind <QQ号>")
                return
            
            target_qq = int(parts[1])
            
            # 获取绑定信息
            binding = self.data_manager.get_binding_by_qq(target_qq)
            if not binding:
                await self.qq_bot.send_group_message(group_id, "该用户未绑定")
                return
            
            # 解绑用户
            success = self.data_manager.unbind_user(target_qq, user_id)
            
            if success:
                # 发送成功消息
                variables = self.message_template.create_manual_bind_variables(
                    target_qq, binding['vrc_user_id'], 
                    binding['vrc_username'], user_id
                )
                message = self.message_template.render('manual_unbind_success', variables)
                await self.qq_bot.send_group_message(group_id, message)
            else:
                await self.qq_bot.send_group_message(group_id, "解绑失败")
                
        except Exception as e:
            logger.exception(f"处理解绑命令失败: {e}")
            await self.qq_bot.send_group_message(group_id, "解绑命令执行失败")
    
    async def _handle_list_command(self, event_data: Dict):
        """处理列表命令"""
        try:
            user_id = event_data.get('user_id')
            group_id = event_data.get('group_id')
            
            # 获取绑定列表
            bindings = self.data_manager.get_all_bindings()
            
            if not bindings:
                await self.qq_bot.send_group_message(group_id, "当前没有绑定记录")
                return
            
            # 构建消息
            message = f"当前绑定记录 (共{len(bindings)}条):\n"
            message += "=" * 30 + "\n"
            
            for binding in bindings[:10]:  # 只显示前10条
                message += f"QQ: {binding['qq_id']} -> VRC: {binding['vrc_username']}\n"
            
            if len(bindings) > 10:
                message += f"... 还有 {len(bindings) - 10} 条记录"
            
            await self.qq_bot.send_group_message(group_id, message)
            
        except Exception as e:
            logger.exception(f"处理列表命令失败: {e}")
            await self.qq_bot.send_group_message(group_id, "列表命令执行失败")
    
    async def _handle_search_command(self, event_data: Dict):
        """处理搜索命令"""
        try:
            message = event_data.get('message', '')
            user_id = event_data.get('user_id')
            group_id = event_data.get('group_id')
            
            # 解析命令：!search <keyword>
            parts = message.split(maxsplit=1)
            if len(parts) != 2:
                await self.qq_bot.send_group_message(group_id, "用法: !search <关键词>")
                return
            
            keyword = parts[1]
            
            # 搜索
            results = self.data_manager.search_bindings(keyword)
            
            if not results:
                await self.qq_bot.send_group_message(group_id, "未找到匹配的记录")
                return
            
            # 构建消息
            message = f"搜索结果 (共{len(results)}条):\n"
            message += "=" * 30 + "\n"
            
            for binding in results[:10]:
                message += f"QQ: {binding['qq_id']} -> VRC: {binding['vrc_username']}\n"
            
            if len(results) > 10:
                message += f"... 还有 {len(results) - 10} 条记录"
            
            await self.qq_bot.send_group_message(group_id, message)
            
        except Exception as e:
            logger.exception(f"处理搜索命令失败: {e}")
            await self.qq_bot.send_group_message(group_id, "搜索命令执行失败")
    
    async def _handle_help_command(self, event_data: Dict):
        """处理帮助命令"""
        try:
            group_id = event_data.get('group_id')
            
            help_message = """
管理员命令列表:
!bind <QQ号> <VRChat用户ID> - 手动绑定用户
!unbind <QQ号> - 解绑用户
!list - 查看所有绑定记录
!search <关键词> - 搜索绑定记录
!help - 显示此帮助信息

VRChat用户ID格式: usr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            """.strip()
            
            await self.qq_bot.send_group_message(group_id, help_message)
            
        except Exception as e:
            logger.exception(f"处理帮助命令失败: {e}")