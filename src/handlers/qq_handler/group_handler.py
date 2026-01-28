import time
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from src.utils import assign_vrc_role
from src.utils import generate_verification_code
from src.core.database.utils import safe_db_operation

logger = logging.getLogger("QQBot.GroupHandler")

class GroupHandler:
    def __init__(self, bot):
        self.bot = bot
        self._handled_flags = set()
        self._pending_bindings: Dict[int, Dict[str, Any]] = {}

    async def handle_request(self, data: Dict[str, Any]):
        """处理加群请求"""
        request_type = data.get("request_type")
        sub_type = data.get("sub_type")
        if request_type == "group" and sub_type in ["add", "invite"]:
            await self._process_group_add(data)

    async def handle_notice(self, data: Dict[str, Any]):
        """处理群通知 (成员增减)"""
        notice_type = data.get("notice_type")
        if notice_type == "group_increase":
            await self._process_group_increase(data)
        elif notice_type == "group_decrease":
            await self._process_group_decrease(data)

    # 验证模式说明：
    # - mixed (混合模式): 用户提交的进群请求将被直接接受并收录global_bindings中，允许用户进群之后再提醒完成其完成绑定操作，
    #                    如果用户在指定时间内未完成绑定则进入无限期禁言状态，完成绑定后自动解除
    # - strict (严格模式): ①优先检测该群是否被以其它方式（例如群管的!bind指令）对于该用户进行了绑定，
    #                     如果已经被绑定，则依然类似于混合行为（即允许进群后再完成绑定），但不同的是，
    #                     如果在配置文件中指定的超时时间内未完成验证操作，则会进行踢出并在群内警报
    #                     ②检查对应群聊是否启用了自动拒绝功能，如果启用，则在验证库中没有记录的情况下，无条件拒绝
    #                     拒绝理由提示用户添加机器人账号为好友完成完整的绑定流程
    #                     如果未启用自动拒绝功能，则仅在群内发出警告，不执行任何操作
    # - disabled (禁用模式): 仅进行登记，只要答案全字匹配某vrc账号或匹配上usrid即可进群，进入登记，但是不进入绑定

    async def _process_group_decrease(self, data: Dict[str, Any]):
        """处理成员退群逻辑"""
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        
        logger.info(f"成员 {user_id} 退出群 {group_id}，正在清理群组绑定记录...")
        logger.debug(f"处理数据: {data}")
        # 只清理群组特定的绑定记录，保留全局绑定记录
        success = await safe_db_operation(self.bot.db.unbind_user_from_group, group_id, user_id)
        if success:
            logger.info(f"已清理成员 {user_id} 在群 {group_id} 的绑定记录")
            logger.debug(f"清理详情: 成功标记={success}")
        else:
            logger.warning(f"清理成员 {user_id} 在群 {group_id} 的绑定记录失败 (可能未绑定)")
            logger.debug(f"清理详情: 成功标记={success}")

    async def _process_group_add(self, data: Dict[str, Any]):
        """处理加群请求逻辑"""
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        comment = data.get("comment", "").strip()
        flag = data.get("flag")
        sub_type = data.get("sub_type", "add")

        # 0. 预检查
        auto_approve_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "auto_approve_group_request", "False")
        if auto_approve_setting.lower() != "true":
            return

        if flag in self._handled_flags:
            return
        self._handled_flags.add(flag)

        # 1. 获取验证模式
        verification_mode = await safe_db_operation(self.bot.db.get_group_setting, group_id, "verification_mode", "mixed")
        auto_reject_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "auto_reject_on_join", "False")
        auto_reject = auto_reject_setting.lower() == "true"

        # 2. 检查是否已在全局验证表中 (全局验证过的用户可以直接通过)
        global_verification = await safe_db_operation(self.bot.db.get_global_verification, user_id)
        if global_verification:
            logger.info(f"用户 {user_id} 已在全局验证表中，自动同意入群申请")
            logger.debug(f"全局验证详情: {global_verification}")
            await self.bot.qq_client.approve_request(flag, sub_type)
            return

        # 3. 尝试自动重连 (已有绑定记录)
        if await self._try_auto_reconnect(user_id, flag, sub_type):
            return

        # 4. 身份识别 (解析附言)
        vrc_user = await self._parse_vrc_user_from_comment(comment)
        if not vrc_user:
            logger.warning(f"无法识别附言中的 VRChat 账号: {comment}")
            logger.debug(f"请求详情: Group={group_id}, User={user_id}, Flag={flag}, SubType={sub_type}")
            # 根据验证模式和自动拒绝设置处理
            if verification_mode == "disabled":
                # 禁用模式下，如果自动拒绝开启，只有在无法识别VRChat账号时才拒绝
                if auto_reject:
                    if sub_type == "add":
                        reason = "请添加拒绝处理账号为好友完成相应的VRC状态验证绑定流程！"
                        await self.bot.qq_client.reject_request(flag, sub_type, reason)
                    return
                else:
                    # 禁用模式：允许进群但不绑定
                    await self.bot.qq_client.approve_request(flag, sub_type)
                    return
            elif auto_reject:
                # 自动拒绝模式
                if sub_type == "add":
                    reason = "请添加拒绝处理账号为好友完成相应的VRC状态验证绑定流程！"
                    await self.bot.qq_client.reject_request(flag, sub_type, reason)
                return
            else:
                # 不自动拒绝，发送群内警告
                warning_msg = f"⚠️ 用户 {user_id} 的入群申请因无法识别VRChat账号而被搁置: {comment}"
                await self.bot.qq_client.send_group_msg(group_id, warning_msg)
                return

        # 5. 根据验证模式处理
        if verification_mode == "strict":
            # 严格模式：优先检查该群是否已通过其他方式绑定
            existing_binding = await safe_db_operation(self.bot.db.get_group_member_binding, group_id, user_id)
            
            if existing_binding:
                # 已绑定：允许进群后再完成验证，但超时未完成则踢出
                self._pending_bindings[user_id] = {
                    "id": vrc_user["id"],
                    "name": vrc_user["displayName"],
                    "time": time.time()
                }
                await self.bot.qq_client.approve_request(flag, sub_type)
                # 这里可以启动一个定时检查，如果用户未在规定时间内完成验证，则踢出
                return
            else:
                # 未绑定：执行完整安全策略检查
                check_passed, reject_reason = await self._check_security_policies(vrc_user, user_id, group_id)
                if not check_passed:
                    await self.bot.qq_client.reject_request(flag, sub_type, reject_reason)
                    return
                
                # 验证通过，放行并缓存
                self._pending_bindings[user_id] = {
                    "id": vrc_user["id"],
                    "name": vrc_user["displayName"],
                    "time": time.time()
                }
                logger.info(f"验证通过，正在同意申请: QQ={user_id}, VRC={vrc_user['displayName']}")
                logger.debug(f"验证详情: Mode={verification_mode}, AutoReject={auto_reject}")
                await self.bot.qq_client.approve_request(flag, sub_type)
        elif verification_mode == "mixed":
            # 混合模式：直接同意申请并收录global_bindings，允许用户进群后再完成绑定
            check_passed, reject_reason = await self._check_security_policies(vrc_user, user_id, group_id)
            if not check_passed:
                await self.bot.qq_client.reject_request(flag, sub_type, reject_reason)
                return
            
            # 验证通过，同意申请并缓存信息
            self._pending_bindings[user_id] = {
                "id": vrc_user["id"],
                "name": vrc_user["displayName"],
                "time": time.time()
            }
            logger.info(f"验证通过，正在同意申请: QQ={user_id}, VRC={vrc_user['displayName']}")
            logger.debug(f"验证详情: Mode={verification_mode}, AutoReject={auto_reject}")
            await self.bot.qq_client.approve_request(flag, sub_type)
        elif verification_mode == "disabled":
            # 禁用模式：只进行登记，不进行绑定
            await self.bot.qq_client.approve_request(flag, sub_type)
            return
        else:
            # 默认为混合模式
            check_passed, reject_reason = await self._check_security_policies(vrc_user, user_id, group_id)
            if not check_passed:
                await self.bot.qq_client.reject_request(flag, sub_type, reject_reason)
                return
            
            self._pending_bindings[user_id] = {
                "id": vrc_user["id"],
                "name": vrc_user["displayName"],
                "time": time.time()
            }
            logger.info(f"验证通过，正在同意申请: QQ={user_id}, VRC={vrc_user['displayName']}")
            logger.debug(f"验证详情: Mode={verification_mode}, AutoReject={auto_reject}")
            await self.bot.qq_client.approve_request(flag, sub_type)

    async def _process_group_increase(self, data: Dict[str, Any]):
        """处理新成员入群逻辑"""
        group_id = data.get("group_id")
        user_id = data.get("user_id")

        # 1. 获取验证模式
        verification_mode = await safe_db_operation(self.bot.db.get_group_setting, group_id, "verification_mode", "mixed")

        # 2. 优先检查全局验证 (自动入群验证)
        global_verification = await safe_db_operation(self.bot.db.get_global_verification, user_id)
        if global_verification:
            await self._handle_auto_verify_success(group_id, user_id, global_verification['vrc_user_id'], global_verification['vrc_display_name'])
            return

        # 3. 检查是否有待处理的申请记录 (从 _process_group_add 传递过来)
        pending = await self._get_pending_binding_info(user_id)
        if pending:
            # 申请时已识别身份，但仍需验证归属权 (防止冒用)
            if verification_mode == "mixed":
                # 混合模式：允许进群后完成绑定，先提醒用户
                await self._initiate_new_verification(group_id, user_id, pending['id'], pending['name'])
                
                # 发送提醒，告知用户需要在指定时间内完成验证
                timeout = self.bot.vrc_config.verification.get("timeout", 300)
                timeout_minutes = timeout // 60
                reminder_msg = f"[CQ:at,qq={user_id}] 欢迎入群！\n您需要在 {timeout_minutes} 分钟内完成VRChat账号验证，否则将进入无限期禁言状态。\n请查看私信获取验证码。"
                await self.bot.qq_client.send_group_msg(group_id, reminder_msg)
            elif verification_mode == "strict":
                # 严格模式：允许进群后完成验证，但如果超时未完成则踢出
                await self._initiate_new_verification(group_id, user_id, pending['id'], pending['name'])
                
                # 发送提醒，告知用户需要在指定时间内完成验证
                timeout = self.bot.vrc_config.verification.get("timeout", 300)
                timeout_minutes = timeout // 60
                reminder_msg = f"[CQ:at,qq={user_id}] 欢迎入群！\n您需要在 {timeout_minutes} 分钟内完成VRChat账号验证，否则将被踢出群聊。\n请查看私信获取验证码。"
                await self.bot.qq_client.send_group_msg(group_id, reminder_msg)
            else:
                # 其他模式或禁用模式，直接发起验证
                await self._initiate_new_verification(group_id, user_id, pending['id'], pending['name'])
            return

        # 4. 无任何信息，发送绑定提醒
        enable_welcome_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "enable_welcome", "True")
        if enable_welcome_setting.lower() == "true":
            reminder = self.bot.message_config.get_message("welcome", "default", default="欢迎！请绑定 VRChat 账号。")
            await self.bot.qq_client.send_group_msg(group_id, f"[CQ:at,qq={user_id}] {reminder}")


    async def _try_auto_reconnect(self, user_id: int, flag: str, sub_type: str) -> bool:
        """尝试基于已有绑定记录自动放行"""
        binding = await safe_db_operation(self.bot.db.get_binding, user_id)
        if binding:
            bound_vrc_id = binding['vrc_user_id']
            try:
                vrc_user = await self.bot.vrc_client.get_user(bound_vrc_id)
                display_name = vrc_user["displayName"] if vrc_user else binding.get('vrc_display_name', '未知用户')
            except Exception as e:
                logger.warning(f"尝试获取最新用户名失败: {e}")
                display_name = binding.get('vrc_display_name', '未知用户')
            
            self._pending_bindings[user_id] = {
                "id": bound_vrc_id,
                "name": display_name,
                "time": time.time()
            }
            logger.info(f"已绑定成员 {user_id} 申请入群，执行自动放行")
            await self.bot.qq_client.approve_request(flag, sub_type)
            return True
        return False

    async def _parse_vrc_user_from_comment(self, comment: str) -> Optional[Dict[str, Any]]:
        """从加群附言中解析 VRChat 用户信息"""
        search_query = comment
        prefixes = ["加群：", "加群:", "vrc:", "vrchat:", "我是", "昵称", "ID:"]
        for p in prefixes:
            if search_query.lower().startswith(p.lower()):
                search_query = search_query[len(p):].strip()
                break
        return await self._find_vrc_user(search_query)

    async def _check_bind_conflict(self, vrc_id: str, user_id: int) -> Optional[int]:
        """检查 VRChat 账号是否已被其他 QQ 绑定，返回冲突的 QQ 号"""
        existing_qq = await safe_db_operation(self.bot.db.get_qq_by_vrc_id, vrc_id)
        if existing_qq and int(existing_qq) != int(user_id):
            return int(existing_qq)
        return None

    async def _check_security_policies(self, vrc_user: Dict[str, Any], user_id: int, group_id: int) -> Tuple[bool, Optional[str]]:
        """执行一系列安全策略检查 (占用、群组、风险账号)"""
        vrc_id = vrc_user["id"]

        # 1. 查重 (用户存在且未被他人占用) - 全局设置，防止跨群占用
        if self.bot.vrc_config.verification.get("check_occupy", True):
            conflict_qq = await self._check_bind_conflict(vrc_id, user_id)
            if conflict_qq:
                reason_tpl = self.bot.message_config.format_message("errors", "reject_already_bound", existing_qq="{existing_qq}", default="账号已被绑定")
                return False, reason_tpl.format(existing_qq=conflict_qq)

        # 2. VRChat 群组验证 - 群组特定设置
        vrc_group_id_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "vrc_group_id", "")
        check_group_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "check_group_membership", str(self.bot.vrc_config.verification.get("check_group_membership", False)))
        check_group_bool = check_group_setting.lower() == "true"
        
        if check_group_bool:
            if not vrc_group_id_setting:
                logger.warning(f"群组 {group_id} 未配置 VRChat 群组 ID，无法进行群组成员资格检查")
                return False, "群组配置错误：未设置 VRChat 群组 ID"
            
            is_member = await self.bot.vrc_client.get_group_member(vrc_group_id_setting, vrc_id)
            if not is_member:
                reason = self.bot.message_config.get_message("errors", "reject_no_group", default="未加入 VRChat 群组")
                return False, reason

        # 3. 风险账号 (Troll) 拦截 - 群组特定设置
        check_troll_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "check_troll", str(self.bot.vrc_config.verification.get("check_troll", False)))
        check_troll_bool = check_troll_setting.lower() == "true"
        if check_troll_bool:
            tags = vrc_user.get("tags", [])
            if "system_probable_troll" in tags:
                reason = self.bot.message_config.get_message("errors", "reject_troll", default="风险账号")
                return False, reason

        return True, None


    async def _get_global_binding_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户的全局绑定信息"""
        binding = await safe_db_operation(self.bot.db.get_binding, user_id)
        if not binding:
            return None
            
        vrc_id = binding['vrc_user_id']
        try:
            vrc_user = await self.bot.vrc_client.get_user(vrc_id)
            vrc_name = vrc_user["displayName"]
        except Exception as e:
            logger.warning(f"获取 VRChat 用户信息失败: {e}")
            vrc_name = binding.get('vrc_display_name', 'VRChat 用户')
            
        return {"vrc_id": vrc_id, "vrc_name": vrc_name}

    async def _get_pending_binding_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的待处理绑定信息"""
        if user_id in self._pending_bindings:
            pending = self._pending_bindings.pop(user_id)
            if time.time() - pending["time"] < 1800: # 30分钟有效期
                return pending
        return None

    async def _handle_auto_verify_success(self, group_id: int, user_id: int, vrc_id: str, vrc_name: str):
        """处理自动验证成功逻辑 (全局验证用户)"""
        logger.info(f"用户 {user_id} 存在全局验证记录 {vrc_name}，自动通过验证")
        
        # 1. 写入群组绑定记录 (从全局验证信息复制)
        await safe_db_operation(self.bot.db.bind_user, user_id, vrc_id, vrc_name, "auto", group_id)
        
        # 2. 自动修改名片
        auto_rename_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "auto_rename", str(self.bot.vrc_config.verification.get("auto_rename", "True")))
        if auto_rename_setting.lower() == "true":

            try:
                await self.bot.qq_client.set_group_card(group_id, user_id, vrc_name)
            except Exception as e:
                logger.warning(f"自动修改名片失败: {e}")
        
        # 3. 发送欢迎消息
        enable_welcome_setting = await safe_db_operation(self.bot.db.get_group_setting, group_id, "enable_welcome", "True")
        if enable_welcome_setting.lower() == "true":
            welcome_message = await safe_db_operation(self.bot.db.get_group_setting, group_id, "welcome_message", "欢迎回来！")
            welcome_msg = welcome_message.format(user_id=user_id, vrc_name=vrc_name)
            await self.bot.qq_client.send_group_msg(group_id, f"[CQ:at,qq={user_id}] {welcome_msg}")
        
        # 4. 尝试分配角色
        await assign_vrc_role(self.bot, vrc_id, group_id)

    async def _initiate_new_verification(self, group_id: int, user_id: int, vrc_id: str, vrc_name: str):
        """发起新的验证流程 (生成验证码)"""
        # 生成验证码
        code = generate_verification_code()
        
        # 保存验证记录
        await safe_db_operation(self.bot.db.add_verification, user_id, vrc_id, vrc_name, code)
        
        # 发送验证提示
        verify_msg = self.bot.message_config.format_message('verification', 'verification_request_template', user_id=user_id, vrc_name=vrc_name, code=code)
        
        await self.bot.qq_client.send_group_msg(group_id, verify_msg)

    async def _find_vrc_user(self, query: str) -> Optional[Dict[str, Any]]:
        """查找 VRChat 用户"""
        if not query: return None
        if query.startswith("usr_"): return await self.bot.vrc_client.get_user(query)
        users = await self.bot.vrc_client.search_user(query)
        if users:
            for u in users:
                if u["displayName"].lower() == query.lower(): return u
            return users[0]
        return None

    async def validate_vrc_user_for_binding(
        self, vrc_query: str, target_qq: int
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        验证 VRChat 用户是否可以绑定
        返回: (user_info, error_message)
        """
        user = await self._find_vrc_user(vrc_query)
        if not user:
            return None, "❌ 未找到对应的 VRChat 用户"
        
        vrc_id = user["id"]
        vrc_name = user["displayName"]
        
        # 检查全局验证表 (如果用户已在全局验证表中，不允许群管修改绑定)
        global_verification = await safe_db_operation(self.bot.db.get_global_verification, target_qq)
        if global_verification and global_verification['vrc_user_id'] != vrc_id:
            return None, f"❌ 绑定失败：该用户已在全局验证表中绑定 VRC 账号 {global_verification['vrc_display_name']}，如需修改请联系机器人超管！"
        
        conflict_qq = await self._check_bind_conflict(vrc_id, target_qq)
        if conflict_qq:
            return None, f"❌ 绑定失败：VRC 账号 {vrc_name} 已被 QQ {conflict_qq} 绑定"
            
        return {"id": vrc_id, "displayName": vrc_name}, None

    async def manual_bind(self, qq_id: int, vrc_query: str, group_id: Optional[int] = None) -> str:
        """手动绑定处理 (供 MessageHandler 调用)"""
        user_info, error = await self.validate_vrc_user_for_binding(vrc_query, qq_id)
        if error: return error
        
        vrc_id = user_info["id"]
        vrc_name = user_info["displayName"]
            
        # 检查本群现有绑定
        if group_id:
             existing_binding = await safe_db_operation(self.bot.db.get_group_member_binding, group_id, qq_id)
             if existing_binding:
                 old_vrc_name = existing_binding.get('vrc_display_name', '未知用户')
                 return f"❌ QQ {qq_id} 在本群已绑定 {old_vrc_name}，如需修改请先解绑"

        # 检查全局绑定 (防止冲突)
        global_binding = await safe_db_operation(self.bot.db.get_binding, qq_id)
        if global_binding:
            # 如果全局绑定来源不是当前群，或者是 manual 类型且没有 origin_group_id (纯全局绑定)
            # 或者有 origin_group_id 但不是当前群
            origin_group = global_binding.get('origin_group_id')
            if origin_group and origin_group != group_id:
                g_vrc_name = global_binding.get('vrc_display_name', '未知')
                g_vrc_id = global_binding.get('vrc_user_id', '未知')
                return f"❌ 登记无效！该用户已全局绑定了VRC账号 {g_vrc_name} ({g_vrc_id})！请联系机器人管理员！"

        success = await safe_db_operation(self.bot.db.bind_user, qq_id, vrc_id, vrc_name, "manual", group_id)
        
        if success:
             return f"✅ 已成功将 QQ {qq_id} 绑定到 VRChat: {vrc_name}"
        else:
            return "❌ 数据库错误"

    async def manual_global_bind(self, qq_id: int, vrc_id: str, vrc_name: str) -> str:
        """手动全局绑定处理 (由超管执行)"""
        # 首先尝试将用户添加到全局验证表
        success = await safe_db_operation(self.bot.db.add_global_verification, qq_id, vrc_id, vrc_name, "admin")
        if not success:
            return "❌ 全局验证记录添加失败"
        
        # 同时在全局绑定表中也记录
        success = await safe_db_operation(self.bot.db.bind_user, qq_id, vrc_id, vrc_name, "manual_global", None)
        if not success:
            return "❌ 全局绑定记录添加失败"
        
        # 为所有已加入的群聊同步绑定记录
        # 这里简单地更新群组表，如果有群组表的话
        return f"✅ 已成功将 QQ {qq_id} 全局绑定到 VRChat: {vrc_name}"