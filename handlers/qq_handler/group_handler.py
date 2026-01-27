import time
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from utils.verification import assign_vrc_role
from utils.code_generator import generate_verification_code

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

    async def _process_group_decrease(self, data: Dict[str, Any]):
        """处理成员退群逻辑"""
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        
        logger.info(f"成员 {user_id} 退出群 {group_id}，正在清理绑定记录...")
        success = await asyncio.to_thread(self.bot.db.unbind_user_from_group, group_id, user_id)
        if success:
            logger.info(f"已清理成员 {user_id} 在群 {group_id} 的绑定记录")
        else:
            logger.warning(f"清理成员 {user_id} 在群 {group_id} 的绑定记录失败 (可能未绑定)")

    async def _process_group_add(self, data: Dict[str, Any]):
        """处理加群请求逻辑"""
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        comment = data.get("comment", "").strip()
        flag = data.get("flag")
        sub_type = data.get("sub_type", "add")

        # 0. 预检查
        if not self.bot.global_config.features.get("auto_approve_group_request", False):
            return

        if flag in self._handled_flags:
            return
        self._handled_flags.add(flag)

        # 1. 尝试自动重连 (已有绑定记录)
        if await self._try_auto_reconnect(user_id, flag, sub_type):
            return

        # 2. 身份识别 (解析附言)
        vrc_user = await self._parse_vrc_user_from_comment(comment)
        if not vrc_user:
            logger.warning(f"无法识别附言中的 VRChat 账号: {comment}")
            if sub_type == "add":
                reason = self.bot.global_config.templates.get("reject_no_user", "无法识别 VRChat 账号")
                await self.bot.qq_client.reject_request(flag, sub_type, reason)
            return

        # 3. 安全与策略检查
        check_passed, reject_reason = await self._check_security_policies(vrc_user, user_id)
        if not check_passed:
            await self.bot.qq_client.reject_request(flag, sub_type, reject_reason)
            return

        # 4. 验证通过，放行并缓存
        self._pending_bindings[user_id] = {
            "id": vrc_user["id"],
            "name": vrc_user["displayName"],
            "time": time.time()
        }
        logger.info(f"验证通过，正在同意申请: QQ={user_id}, VRC={vrc_user['displayName']}")
        await self.bot.qq_client.approve_request(flag, sub_type)

    async def _process_group_increase(self, data: Dict[str, Any]):
        """处理新成员入群逻辑"""
        group_id = data.get("group_id")
        user_id = data.get("user_id")

        # 1. 优先检查全局绑定 (自动入群验证)
        global_bind = await self._get_global_binding_info(user_id)
        if global_bind:
            await self._handle_auto_verify_success(group_id, user_id, global_bind['vrc_id'], global_bind['vrc_name'])
            return

        # 2. 检查是否有待处理的申请记录 (从 _process_group_add 传递过来)
        pending = await self._get_pending_binding_info(user_id)
        if pending:
            # 申请时已识别身份，但仍需验证归属权 (防止冒用)
            await self._initiate_new_verification(group_id, user_id, pending['id'], pending['name'])
            return

        # 3. 无任何信息，发送绑定提醒
        if self.bot.global_config.enable_welcome:
            reminder = self.bot.global_config.templates.get("reminder_not_bound", "欢迎！请绑定 VRChat 账号。")
            await self.bot.qq_client.send_group_msg(group_id, f"[CQ:at,qq={user_id}] {reminder}")


    async def _try_auto_reconnect(self, user_id: int, flag: str, sub_type: str) -> bool:
        """尝试基于已有绑定记录自动放行"""
        binding = await asyncio.to_thread(self.bot.db.get_binding, user_id)
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
        existing_qq = await asyncio.to_thread(self.bot.db.get_qq_by_vrc_id, vrc_id)
        if existing_qq and int(existing_qq) != int(user_id):
            return int(existing_qq)
        return None

    async def _check_security_policies(self, vrc_user: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[str]]:
        """执行一系列安全策略检查 (占用、群组、风险账号)"""
        vrc_id = vrc_user["id"]

        # 1. 查重 (用户存在且未被他人占用)
        if self.bot.vrc_config.verification.get("check_occupy", True):
            conflict_qq = await self._check_bind_conflict(vrc_id, user_id)
            if conflict_qq:
                reason_tpl = self.bot.global_config.templates.get("reject_already_bound", "账号已被绑定")
                return False, reason_tpl.format(existing_qq=conflict_qq)

        # 2. VRChat 群组验证
        vrc_group_id = self.bot.vrc_config.verification.get("group_id")
        check_group = self.bot.vrc_config.verification.get("check_group_membership", False)
        
        if check_group and vrc_group_id:
            is_member = await self.bot.vrc_client.get_group_member(vrc_group_id, vrc_id)
            if not is_member:
                reason = self.bot.global_config.templates.get("reject_no_group", "未加入 VRChat 群组")
                return False, reason

        # 3. 风险账号 (Troll) 拦截
        if self.bot.vrc_config.verification.get("check_troll", False):
            tags = vrc_user.get("tags", [])
            if "system_probable_troll" in tags:
                reason = self.bot.global_config.templates.get("reject_troll", "风险账号")
                return False, reason

        return True, None


    async def _get_global_binding_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户的全局绑定信息"""
        binding = await asyncio.to_thread(self.bot.db.get_binding, user_id)
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
        """处理自动验证成功逻辑 (全局绑定用户)"""
        logger.info(f"用户 {user_id} 存在全局绑定 {vrc_name}，自动通过验证")
        
        # 1. 写入群组绑定记录
        await asyncio.to_thread(self.bot.db.bind_user, user_id, vrc_id, vrc_name, "auto", group_id)
        
        # 2. 自动修改名片
        if self.bot.vrc_config.verification.get("auto_rename", True):
            try:
                await self.bot.qq_client.set_group_card(group_id, user_id, vrc_name)
            except Exception as e:
                logger.warning(f"自动修改名片失败: {e}")
        
        # 3. 发送欢迎消息
        welcome_tpl = (
            "[CQ:at,qq={user_id}] 欢迎回来！\n"
            "已检测到您的全局绑定记录，自动完成身份验证。\n"
            "当前绑定账号: {vrc_name}"
        )
        await self.bot.qq_client.send_group_msg(group_id, welcome_tpl.format(user_id=user_id, vrc_name=vrc_name))
        
        # 4. 尝试分配角色
        await assign_vrc_role(self.bot, vrc_id)

    async def _initiate_new_verification(self, group_id: int, user_id: int, vrc_id: str, vrc_name: str):
        """发起新的验证流程 (生成验证码)"""
        # 生成验证码
        code = generate_verification_code()
        
        # 保存验证记录
        await asyncio.to_thread(self.bot.db.add_verification, user_id, vrc_id, vrc_name, code)
        
        # 发送验证提示
        default_tpl = (
            "[CQ:at,qq={user_id}] 欢迎加入！\n"
            "您申请绑定的VRChat账号为: {vrc_name}\n"
            "将VRChat状态描述修改为以下数字：\n"
            "{code}\n"
            "修改完成后，请在群内发送 !verify 完成验证。"
        )
        verify_tpl = self.bot.global_config.templates.get("verification_request", default_tpl)
        verify_msg = verify_tpl.format(user_id=user_id, vrc_name=vrc_name, code=code)
        
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
             existing_binding = await asyncio.to_thread(self.bot.db.get_group_member_binding, group_id, qq_id)
             if existing_binding:
                 old_vrc_name = existing_binding.get('vrc_display_name', '未知用户')
                 return f"❌ QQ {qq_id} 在本群已绑定 {old_vrc_name}，如需修改请先解绑"

        # 检查全局绑定 (防止冲突)
        global_binding = await asyncio.to_thread(self.bot.db.get_binding, qq_id)
        if global_binding:
            # 如果全局绑定来源不是当前群，或者是 manual 类型且没有 origin_group_id (纯全局绑定)
            # 或者有 origin_group_id 但不是当前群
            origin_group = global_binding.get('origin_group_id')
            if origin_group and origin_group != group_id:
                g_vrc_name = global_binding.get('vrc_display_name', '未知')
                g_vrc_id = global_binding.get('vrc_user_id', '未知')
                return f"❌ 登记无效！该用户已全局绑定了VRC账号 {g_vrc_name} ({g_vrc_id})！请联系机器人管理员！"

        success = await asyncio.to_thread(self.bot.db.bind_user, qq_id, vrc_id, vrc_name, "manual", group_id)
        
        if success:
             return f"✅ 已成功将 QQ {qq_id} 绑定到 VRChat: {vrc_name}"
        else:
            return "❌ 数据库错误"
