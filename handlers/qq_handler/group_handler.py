import time
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("QQBot.GroupHandler")

class GroupHandler:
    def __init__(self, bot):
        self.bot = bot
        self._handled_flags = set()
        self._pending_bindings: Dict[int, Dict[str, Any]] = {}

    async def handle_request(self, data: Dict[str, Any]):
        request_type = data.get("request_type")
        sub_type = data.get("sub_type")
        if request_type == "group" and sub_type in ["add", "invite"]:
            await self._process_group_add(data)

    async def handle_notice(self, data: Dict[str, Any]):
        notice_type = data.get("notice_type")
        if notice_type == "group_increase":
            await self._process_group_increase(data)

    async def _process_group_add(self, data: Dict[str, Any]):
        group_id = data.get("group_id")
        user_id = data.get("user_id")
        comment = data.get("comment", "").strip()
        flag = data.get("flag")
        sub_type = data.get("sub_type", "add")

        if flag in self._handled_flags:
            return
        self._handled_flags.add(flag)

        if group_id not in self.bot.global_config.group_whitelist:
            return

        # 1. 自动重连逻辑
        bound_vrc_id = await asyncio.to_thread(self.bot.db.get_vrc_id_by_qq, user_id)
        if bound_vrc_id:
            vrc_user = await self.bot.vrc_client.get_user(bound_vrc_id)
            if vrc_user:
                self._pending_bindings[user_id] = {"id": bound_vrc_id, "name": vrc_user["displayName"], "time": time.time()}
                logger.info(f"已绑定成员 {user_id} 申请入群，执行自动放行")
                await self.bot.qq_client.approve_request(flag, sub_type)
                return

        # 2. 身份识别
        search_query = comment
        prefixes = ["加群：", "加群:", "vrc:", "vrcat:", "vrchat:", "我是", "昵称", "ID:"]
        for p in prefixes:
            if search_query.lower().startswith(p.lower()):
                search_query = search_query[len(p):].strip()
                break
        
        vrc_user = await self._find_vrc_user(search_query)
        if not vrc_user:
            logger.warning(f"无法识别附言中的 VRChat 账号: {comment}")
            if sub_type == "add":
                reason = self.bot.global_config.templates.get("reject_no_user", "无法识别 VRChat 账号")
                await self.bot.qq_client.reject_request(flag, sub_type, reason)
            return

        vrc_id = vrc_user["id"]
        vrc_name = vrc_user["displayName"]

        # 3. 查重 (用户存在且未被他人占用)
        if self.bot.vrc_config.verification.get("check_occupy", True):
            existing_qq = await asyncio.to_thread(self.bot.db.get_qq_by_vrc_id, vrc_id)
            if existing_qq and int(existing_qq) != int(user_id):
                reason_tpl = self.bot.global_config.templates.get("reject_already_bound", "账号已被绑定")
                reason = reason_tpl.format(existing_qq=existing_qq)
                await self.bot.qq_client.reject_request(flag, sub_type, reason)
                return

        # 4. 群组验证
        vrc_group_id = self.bot.vrc_config.verification.get("group_id")
        check_group = self.bot.vrc_config.verification.get("check_group_membership", False)
        
        if check_group and vrc_group_id:
            is_member = await self.bot.vrc_client.get_group_member(vrc_group_id, vrc_id)
            if not is_member:
                reason = self.bot.global_config.templates.get("reject_no_group", "未加入 VRChat 群组")
                await self.bot.qq_client.reject_request(flag, sub_type, reason)
                return

        # 5. 风险账号 (Troll) 拦截
        if self.bot.vrc_config.verification.get("check_troll", False):
            tags = vrc_user.get("tags", [])
            # system_probable_troll: 官方标记的风险账号 (Nuisance)
            if "system_probable_troll" in tags:
                reason = self.bot.global_config.templates.get("reject_troll", "风险账号")
                await self.bot.qq_client.reject_request(flag, sub_type, reason)
                return

        self._pending_bindings[user_id] = {"id": vrc_id, "name": vrc_name, "time": time.time()}
        logger.info(f"验证通过，正在同意申请: QQ={user_id}, VRC={vrc_name}")
        await self.bot.qq_client.approve_request(flag, sub_type)

    async def _process_group_increase(self, data: Dict[str, Any]):
        group_id = data.get("group_id")
        user_id = data.get("user_id")

        if group_id not in self.bot.global_config.group_whitelist:
            return

        vrc_id = None
        vrc_name = None

        db_vrc_id = await asyncio.to_thread(self.bot.db.get_vrc_id_by_qq, user_id)
        if db_vrc_id:
            vrc_id = db_vrc_id
            vrc_user = await self.bot.vrc_client.get_user(vrc_id)
            vrc_name = vrc_user["displayName"] if vrc_user else "VRChat 用户"
        elif user_id in self._pending_bindings:
            pending = self._pending_bindings.pop(user_id)
            if time.time() - pending["time"] < 1800:
                vrc_id = pending["id"]
                vrc_name = pending["name"]
                await asyncio.to_thread(self.bot.db.bind_user, user_id, vrc_id, vrc_name, "auto")

        if vrc_id and vrc_name:
            if self.bot.vrc_config.verification.get("auto_rename"):
                await self.bot.qq_client.set_group_card(group_id, user_id, vrc_name)
            
            if self.bot.vrc_config.verification.get("auto_assign_role"):
                vrc_group_id = self.bot.vrc_config.verification.get("group_id")
                target_role_id = self.bot.vrc_config.verification.get("target_role_id")
                if vrc_group_id and target_role_id:
                    await self.bot.vrc_client.add_group_role(vrc_group_id, vrc_id, target_role_id)

            if self.bot.global_config.enable_welcome:
                welcome_tpl = self.bot.global_config.templates.get("welcome", "")
                if welcome_tpl:
                    msg = welcome_tpl.format(display_name=vrc_name, user_id=user_id)
                    await self.bot.qq_client.send_group_msg(group_id, msg)
        else:
            if self.bot.global_config.enable_welcome:
                reminder = self.bot.global_config.templates.get("reminder_not_bound", "欢迎！请绑定 VRChat 账号。")
                await self.bot.qq_client.send_group_msg(group_id, f"[CQ:at,qq={user_id}] {reminder}")

    async def _find_vrc_user(self, query: str) -> Optional[Dict[str, Any]]:
        if not query: return None
        if query.startswith("usr_"): return await self.bot.vrc_client.get_user(query)
        users = await self.bot.vrc_client.search_user(query)
        if users:
            for u in users:
                if u["displayName"].lower() == query.lower(): return u
            return users[0]
        return None

    async def manual_bind(self, qq_id: int, vrc_query: str) -> str:
        user = await self._find_vrc_user(vrc_query)
        if not user: return "❌ 未找到对应的 VRChat 用户"
        
        vrc_id = user["id"]
        vrc_name = user["displayName"]
        
        existing_qq = await asyncio.to_thread(self.bot.db.get_qq_by_vrc_id, vrc_id)
        if existing_qq and int(existing_qq) != int(qq_id):
            return f"❌ 绑定失败：VRC 账号 {vrc_name} 已被 QQ {existing_qq} 绑定"
            
        success = await asyncio.to_thread(self.bot.db.bind_user, qq_id, vrc_id, vrc_name, "manual")
        return f"✅ 已成功将 QQ {qq_id} 绑定到 VRChat: {vrc_name}" if success else "❌ 数据库错误"
