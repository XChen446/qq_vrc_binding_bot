import time
import logging
import asyncio
import os
from typing import Dict, Any, List, Optional, Tuple
from src.utils.image_generator import generate_binding_list_image
from src.utils.verification import calculate_verification_elapsed, assign_vrc_role
from src.utils.code_generator import generate_verification_code
from src.core.database.utils import safe_db_operation
from src.utils.admin_utils import is_super_admin, is_group_admin_or_owner
from src.handlers.qq_handler.command_handler import CommandHandler

logger = logging.getLogger("QQBot.MessageHandler")

async def _generate_list_image(results: List[Dict], has_more: bool, total_count: int, limit: int, is_global: bool = False) -> str:
    temp_dir = "data/temp"
    os.makedirs(temp_dir, exist_ok=True)
    filename = f"{'global_' if is_global else ''}bindings_{int(time.time())}.png"
    output_path = os.path.join(temp_dir, filename)
    abs_output_path = os.path.abspath(output_path)

    try:
        await asyncio.to_thread(generate_binding_list_image, results, abs_output_path)
        reply = f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
        if has_more:
            reply += f"\n(仅显示前 {limit} 条，共 {total_count} 条)"
        return reply
    except Exception as e:
        logger.error(f"生成绑定列表图片失败: {e}")
        return f"❌ 生成图片失败: {e}"


class MessageHandler:
    def __init__(self, bot, config_path: str = None):
        self.bot = bot
        self.config_path = config_path
        self._command_cooldowns: Dict[str, Dict[int, float]] = {}
        self.command_handler = CommandHandler(bot)
        
        self._command_handlers: Dict[str, any] = {
            "help": self._cmd_help,
            "instances": self._cmd_instances,
            "code": self._cmd_code,
            "verify": self._cmd_verify,
            "bind": self._cmd_bind,
            "unbind": self._cmd_unbind,
            "list": self._cmd_list,
            "unbound": self._cmd_unbound,
            "search": self._cmd_search,
            "query": self._cmd_query,
            "me": self._cmd_me,
            "admin": self._cmd_admin,
            "glbind": self._cmd_glbind,
            "unglbind": self._cmd_unglbind,
            "unlist": self._cmd_unlist,
            "set": self._cmd_set
        }

    def _get_command_config(self, command: str) -> Dict[str, Any]:
        return self.bot.global_config.commands.get(command, {})

    def _is_command_enabled(self, command: str) -> bool:
        return self._get_command_config(command).get("enabled", True)

    def _check_cooldown(self, command: str, user_id: int) -> bool:
        config = self._get_command_config(command)
        cooldown = config.get("cooldown", 3)
        now = time.time()
        
        if command not in self._command_cooldowns:
            self._command_cooldowns[command] = {}
            
        last_time = self._command_cooldowns[command].get(user_id, 0)
        if now - last_time < cooldown:
            return False
            
        self._command_cooldowns[command][user_id] = now
        return True

    async def handle_message(self, data: Dict[str, Any]):
        user_id = data.get("user_id")
        group_id = data.get("group_id")
        raw_message = data.get("raw_message", "").strip()
        
        if not raw_message.startswith("!"):
            return

        parts = raw_message.split()
        command = parts[0][1:].lower()
        args = parts[1:]
        
        source = f"Group({group_id})" if group_id else f"Private({user_id})"
        logger.info(f"收到指令: {command} | Args: {args} | User: {user_id} | Source: {source}")

        if not self._is_command_enabled(command):
            logger.debug(f"指令未启用: {command}")
            return

        if not self._check_cooldown(command, user_id):
            logger.debug(f"指令冷却中: {command} (User: {user_id})")
            return
        
        try:
            result = await self._handle_command(command, args, data)
            if result:
                reply_log = str(result)
                reply_display = reply_log[:100] + '...' if len(reply_log) > 100 else reply_log
                logger.info(f"指令处理完成: {command} | Reply: {reply_display}")
            else:
                logger.info(f"指令处理完成: {command} | No Reply")
        except Exception as e:
            logger.error(f"指令处理异常: {command} | Error: {e}")
            await self._reply(data, f"❌ 指令执行出错: {e}")

    async def _is_user_group_admin_or_owner(self, user_id: int, group_id: Optional[int] = None) -> bool:
        """验证用户是否为群管理员或群主"""
        if is_super_admin(user_id, self.bot.global_config.admin_qq):
            return True
            
        if not group_id:
            return False
            
        # 使用 NapCat API 获取真实的群成员角色信息
        return await is_group_admin_or_owner(user_id, group_id, self.bot.qq_client)

    async def _handle_command(self, command: str, args: list, context: Dict[str, Any]):
        user_id = context.get("user_id")
        group_id = context.get("group_id")
        is_admin = await self._is_user_group_admin_or_owner(user_id, group_id)
        
        cmd_config = self._get_command_config(command)
        if cmd_config.get("admin_only", False) and not is_admin:
            return
        
        handler = self._command_handlers.get(command)
        if handler:
            try:
                reply = await handler(args, context, is_admin)
                if reply:
                    await self._reply(context, reply)
                    return reply
            except Exception as e:
                logger.error(f"指令 {command} 执行出错: {e}")
                await self._reply(context, f"❌ 指令执行出错: {e}")

    async def _reply(self, context: Dict[str, Any], message: str):
        group_id = context.get("group_id")
        user_id = context.get("user_id")
        
        if group_id:
            await self.bot.qq_client.send_group_msg(group_id, message)
        else:
            await self.bot.qq_client.send_private_msg(user_id, message)
        
        return message

    async def _cmd_help(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        binding = await safe_db_operation(self.bot.db.get_binding, user_id)

        help_lines = ["VRChat 机器人指令列表:"]
        commands_help = {
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
        }
        
        for cmd, desc in commands_help.items():
            cfg = self._get_command_config(cmd)
            if not cfg.get("enabled", True):
                continue
            if cfg.get("admin_only", False) and not is_admin:
                continue
            
            if cmd == "unbound" and not is_admin:
                continue
            
            if cmd in ["admin", "glbind", "unglbind", "set"] and not is_super_admin(user_id, self.bot.global_config.admin_qq):
                continue

            if binding and cmd in ["verify", "code"]:
                continue

            help_lines.append(f"!{cmd} - {desc}")
            
        help_lines.append("!help - 显示此帮助信息")
        return "\n".join(help_lines)

    async def _cmd_instances(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        group_id = context.get("group_id")
        if not group_id:
            return "❌ 该指令仅限在群聊中使用喵~"
        return await self.bot.vrc_handler.handle_instances_command(group_id)

    async def _check_user_bind_status(self, user_id: int) -> Tuple[Optional[Dict], Optional[Dict], Optional[str]]:
        """检查用户绑定和验证状态，返回 (binding, verification, reply_msg_if_bound)"""
        binding = await safe_db_operation(self.bot.db.get_binding, user_id)
        if binding:
            return binding, None, f"✅ 您已绑定 VRChat 账号 ({binding['vrc_display_name']})。"
        
        verification = await safe_db_operation(self.bot.db.get_verification, user_id)
        return None, verification, None

    async def _refresh_verification_code(self, user_id: int, vrc_id: str, vrc_name: str) -> Dict[str, Any]:
        """重新生成并保存验证码"""
        code = generate_verification_code()
        await safe_db_operation(self.bot.db.add_verification, user_id, vrc_id, vrc_name, code)
        return await safe_db_operation(self.bot.db.get_verification, user_id)

    async def _cmd_code(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        group_id = context.get("group_id")
        
        binding, verification, reply = await self._check_user_bind_status(user_id)
        if reply: return reply
        
        if not verification:
            vrc_info = await safe_db_operation(self.bot.db.get_pending_vrc_info, user_id)
            if not vrc_info:
                return "❌ 您当前没有待验证的请求。请先使用 !bind [VRChat名字] 申请绑定，或联系管理员。"
            
            # 生成新的验证码
            vrc_id = vrc_info.get("vrc_user_id")
            vrc_name = vrc_info.get("vrc_display_name")
            if not vrc_id or not vrc_name:
                return "❌ 无法获取您的VRChat信息，请重新申请绑定。"
            
            # 创建新的验证记录
            verification = await self._refresh_verification_code(user_id, vrc_id, vrc_name)
            if not verification:
                return "❌ 生成验证码失败，请稍后重试。"
            
            expiry_seconds = self.bot.vrc_config.verification.get("code_expiry", 300)
            elapsed = 0  # 新生成的验证码，时间为0
            
        else:
            # 已有验证记录，检查是否过期
            if verification.get('is_expired'):
                # 重新生成验证码
                verification = await self._refresh_verification_code(
                    user_id, verification["vrc_user_id"], verification["vrc_display_name"]
                )
                
                expiry_seconds = self.bot.vrc_config.verification.get("code_expiry", 300)
                elapsed = 0
            else:
                expiry_seconds = self.bot.vrc_config.verification.get("code_expiry", 300)
                elapsed = calculate_verification_elapsed(verification)
                
                if elapsed > expiry_seconds:
                    await safe_db_operation(self.bot.db.mark_verification_expired, user_id)
                    # 重新生成验证码
                    verification = await self._refresh_verification_code(user_id, verification["vrc_user_id"], verification["vrc_display_name"])
                    
                    elapsed = 0

        remaining = int(expiry_seconds - elapsed)
        code = verification['code']
        vrc_name = verification['vrc_display_name']
        
        return f"您的验证码是: {code}\n有效时间剩余: {remaining}秒\n请将 VRChat 状态描述修改为此验证码，然后发送 !verify\n目标VRChat账号: {vrc_name}"

    async def _cmd_verify(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        group_id = context.get("group_id")
        
        binding, verification, reply = await self._check_user_bind_status(user_id)
        if binding:
             return f"✅ 您已绑定 VRChat 账号 ({binding['vrc_display_name']})，无需再次验证。"
        
        if not verification:
            return "❌ 您当前没有待验证的请求。如果您刚进群，请检查是否已绑定 VRChat 账号。"
            
        vrc_id = verification["vrc_user_id"]
        code = verification["code"]
        vrc_name = verification["vrc_display_name"]
        expiry_seconds = self.bot.vrc_config.verification.get("code_expiry", 300)
        elapsed = calculate_verification_elapsed(verification)

        if verification.get("is_expired") or elapsed > expiry_seconds:
            return "❌ 验证码已过期，请使用!code重新获取。"
        
        try:
            vrc_user = await self.bot.vrc_client.get_user(vrc_id)
            if not vrc_user:
                return "❌ 无法获取 VRChat 用户信息，请稍后再试。"
            
            status_desc = vrc_user.get("statusDescription", "")
            if code in status_desc:
                # 首先检查用户是否已在全局验证表中
                global_verification = await safe_db_operation(self.bot.db.get_global_verification, user_id)
                if global_verification:
                    # 用户已在全局验证表中，直接使用可信数据
                    bind_result = await safe_db_operation(self.bot.db.bind_user, user_id, global_verification["vrc_user_id"], global_verification["vrc_display_name"], "verified", group_id)
                else:
                    # 用户不在全局验证表中，使用当前验证的数据
                    bind_result = await safe_db_operation(self.bot.db.bind_user, user_id, vrc_id, vrc_name, "verified", group_id)
                
                delete_result = await safe_db_operation(self.bot.db.delete_verification, user_id)
                
                if not bind_result or not delete_result:
                    return "❌ 验证成功但保存数据失败，请联系管理员。"
                
                # 如果是首次验证，将其添加到全局验证表
                if not global_verification:
                    await safe_db_operation(self.bot.db.add_global_verification, user_id, vrc_id, vrc_name, "verified")
                
                reply = f"✅ 验证成功！已绑定 VRChat 账号: {vrc_name}"
                
                if group_id:
                    if self.bot.vrc_config.verification.get("auto_rename"):
                        try:
                            await self.bot.qq_client.set_group_card(group_id, user_id, vrc_name)
                        except Exception as e:
                            logger.warning(f"改名失败: {e}")
                    
                    if self.bot.vrc_config.verification.get("auto_assign_role"):
                        await assign_vrc_role(self.bot, vrc_id)

                    # 获取群组设置来决定是否发送欢迎消息
                    enable_welcome = await safe_db_operation(self.bot.db.get_group_setting, group_id, "enable_welcome", "True")
                    if enable_welcome.lower() == "true":
                        welcome_message = await safe_db_operation(self.bot.db.get_group_setting, group_id, "welcome_message", "欢迎！")
                        welcome_tpl = welcome_message.format(display_name=vrc_name, user_id=user_id)
                        reply += f"\n{welcome_tpl}"
                
                return reply
            else:
                return f"❌ 验证失败。\n要求状态描述包含: {code}\n当前状态描述: {status_desc or '(空)'}\n请修改后再次输入 !verify"
        except Exception as e:
            logger.error(f"验证过程出错: {e}")
            return f"❌ 验证过程出错: {e}"

    async def _cmd_bind(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        group_id = context.get("group_id")
        if not group_id:
             return "❌ 该指令仅限在群聊中使用"

        if len(args) < 2:
            return "用法: !bind [QQ号] [VRChat ID/名字]"
        
        target_qq = int(args[0])

        # 检查QQ号是否在本群
        member_info = await self.bot.qq_client.get_group_member_info(group_id, target_qq)
        if not member_info:
            return f"❌ 无法绑定：QQ号 {target_qq} 不在本群中"

        vrc_query = " ".join(args[1:])
        return await self.bot.group_handler.manual_bind(target_qq, vrc_query, group_id)

    async def _cmd_unbind(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        group_id = context.get("group_id")
        user_id = context.get("user_id")
        
        if not group_id:
             return "❌ 该指令仅限在群聊中使用"

        if len(args) < 1:
            return "用法: !unbind [QQ号]"
        
        target_qq = int(args[0])

        # 检查QQ号是否在本群
        member_info = await self.bot.qq_client.get_group_member_info(group_id, target_qq)
        if not member_info:
            return f"❌ 无法解绑：QQ号 {target_qq} 不在本群中"

        if not is_admin:
            return None
        
        # 检查用户是否在全局验证表中
        global_verification = await safe_db_operation(self.bot.db.get_global_verification, target_qq)
        if global_verification:
            # 如果在全局验证表中，群管只能解绑群组记录，不能影响全局验证
            success = await safe_db_operation(self.bot.db.unbind_user_from_group, group_id, target_qq)
            if success:
                return f"✅ 已从本群解绑 QQ: {target_qq}，但该用户仍在全局验证表中"
            else:
                return f"❌ 解绑失败，该用户可能未绑定或已解绑"
        else:
            # 如果不在全局验证表中，群管可以解绑群组记录
            success = await safe_db_operation(self.bot.db.unbind_user_from_group, group_id, target_qq)
            return f"✅ 已从本群解绑 QQ: {target_qq}" if success else f"❌ 解绑失败，该用户可能未绑定或已解绑"

    async def _cmd_list(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        # 1. 检查是否在群聊中使用
        group_id = context.get("group_id")
        
        # 2. 只有超级管理员可以查看全局列表 (使用 'global' 参数)
        if args and args[0] == "global":
            user_id = context.get("user_id")
            if not is_super_admin(user_id, self.bot.global_config.admin_qq):
                return None
            
            # 全局列表逻辑
            try:
                bindings = await safe_db_operation(self.bot.db.search_global_bindings, "")
                if not bindings:
                    return "目前没有已绑定的用户"
                
                # 获取QQ昵称
                data = await self._fetch_qq_names(bindings)
                
                # 生成图片
                from src.utils import generate_list_image
                temp_dir = "data/temp"
                os.makedirs(temp_dir, exist_ok=True)
                filename = f"list_global_{int(time.time())}.png"
                output_path = os.path.join(temp_dir, filename)
                abs_output_path = os.path.abspath(output_path)
                
                await asyncio.to_thread(generate_list_image, data, "Global Bindings", abs_output_path)
                
                return f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
            except Exception as e:
                logger.error(f"生成全局列表失败: {e}")
                return f"❌ 生成列表失败: {e}"

        # 3. 处理 !list 后面跟参数的情况 (尝试绑定 VRChat 群组)
        if args:
            if not group_id:
                return "❌ 绑定群组指令仅限在群聊中使用"
                
                if not is_admin:
                    return None
                
            vrc_group_id = args[0]
            
            # 检查是否已经绑定了
            current_binding = await safe_db_operation(self.bot.db.get_group_vrc_group_id, group_id)
            if current_binding:
                return "❌ 绑定失败！本群已绑定了 VRChat 群组！请联系机器人管理员！"
            
            # 执行绑定
            success = await safe_db_operation(self.bot.db.set_group_vrc_group_id, group_id, vrc_group_id)
            if success:
                return f"✅ 已成功将本群绑定到 VRChat 群组: {vrc_group_id}"
            else:
                return "❌ 绑定失败: 数据库操作错误"

        # 4. 默认逻辑：显示本群列表
        if not group_id:
            return "❌ 请在群聊中使用此命令，或私聊使用 !list global (仅限超级管理员)"
            
        try:
            # 优先检查是否绑定了 VRChat 群组
            vrc_group_id = await safe_db_operation(self.bot.db.get_group_vrc_group_id, group_id)
            if vrc_group_id:
                # TODO: 这里应该调用 VRChat API 获取群组成员列表，但目前先显示提示
                # 暂时还是显示数据库中的绑定列表，后续可以扩展为显示 VRChat 群组成员
                pass

            # 获取群绑定记录
            bindings = await safe_db_operation(self.bot.db.get_group_bindings, group_id)
            if not bindings:
                return "本群尚无已绑定的用户"
            
            # 获取QQ昵称
            data = await self._fetch_qq_names(bindings, group_id)
            
            # 生成图片
            from src.utils import generate_list_image
            temp_dir = "data/temp"
            os.makedirs(temp_dir, exist_ok=True)
            filename = f"list_{group_id}_{int(time.time())}.png"
            output_path = os.path.join(temp_dir, filename)
            abs_output_path = os.path.abspath(output_path)
            
            await asyncio.to_thread(generate_list_image, data, f"Group {group_id} Bindings", abs_output_path)
            
            return f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
            
        except Exception as e:
            logger.error(f"查询群绑定记录失败: {e}")
            return f"❌ 查询失败: {e}"

    async def _fetch_qq_names(self, bindings: List[Dict], default_group_id: int = None) -> List[Dict]:
        results = []
        for binding in bindings:
            qq_id = binding.get("qq_id")
            vrc_name = binding.get("vrc_display_name", "Unknown")
            vrc_id = binding.get("vrc_user_id", "Unknown")
            origin_group = binding.get("origin_group_id") or default_group_id
            
            try:
                if origin_group:
                    qq_name = await self.bot.qq_client.get_group_member_info(origin_group, qq_id)
                    qq_display = qq_name.get("card") or qq_name.get("nickname") or str(qq_id)
                else:
                    qq_display = str(qq_id)
            except:
                qq_display = str(qq_id)
            
            item = {
                "qq_id": qq_id,
                "qq_name": qq_display,
                "vrc_name": vrc_name,
                "vrc_id": vrc_id
            }
            
            if binding.get("origin_group_id"):
                item["origin_group_id"] = binding.get("origin_group_id")
                
            results.append(item)
        
        return results

    async def _cmd_unbound(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        if not is_admin:
            return None
        
        target_group = context.get("group_id")
        if not target_group:
            return "❌ 该指令仅限在群聊中使用"
        
        try:
            members = await self.bot.qq_client.get_group_member_list(target_group)
            bindings = await safe_db_operation(self.bot.db.get_group_bindings, target_group)
            
            bound_qqs = {b["qq_id"] for b in bindings}
            unbound_members = [m for m in members if m["user_id"] not in bound_qqs]
            
            if not unbound_members:
                return "✅ 该群所有成员均已绑定 VRChat 账号"
            
            unbound_list = []
            for member in unbound_members[:50]:
                display_name = member.get("card") or member.get("nickname") or str(member["user_id"])
                unbound_list.append(f"{display_name} ({member['user_id']})")
            
            reply = f"群 {target_group} 中未绑定 VRChat 的成员:\n" + "\n".join(unbound_list)
            
            if len(unbound_members) > 50:
                reply += f"\n... 还有 {len(unbound_members) - 50} 人"
            
            return reply
            
        except Exception as e:
            logger.error(f"查询未绑定成员失败: {e}")
            return f"❌ 查询失败: {e}"

    async def _cmd_search(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        if not args:
            return "用法: !search [VRChat 用户名或ID]"
        
        query = " ".join(args)
        
        try:
            users = await self.bot.vrc_client.search_users(query)
            if not users:
                return f"❌ 未找到用户: {query}"
            
            reply = f"找到 {len(users)} 个用户:\n"
            for user in users[:10]:
                display_name = user.get("displayName", "Unknown")
                user_id = user.get("id", "Unknown")
                status = user.get("status", "Unknown")
                reply += f"\n{display_name} ({user_id}) - {status}"
            
            if len(users) > 10:
                reply += f"\n... 还有 {len(users) - 10} 人"
            
            return reply
            
        except Exception as e:
            logger.error(f"搜索用户失败: {e}")
            return f"❌ 搜索失败: {e}"

    async def _cmd_query(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        if not args:
            return "用法: !query [VRChat 用户名或ID]"
        
        query = " ".join(args)
        
        try:
            bindings = await safe_db_operation(self.bot.db.search_bindings, query)
            if not bindings:
                return f"❌ 未找到绑定记录: {query}"
            
            reply = f"找到 {len(bindings)} 条绑定记录:\n"
            for binding in bindings:
                qq_id = binding.get("qq_id", "Unknown")
                vrc_name = binding.get("vrc_display_name", "Unknown")
                origin_group = binding.get("origin_group_id", "Unknown")
                reply += f"\nQQ: {qq_id} -> VRChat: {vrc_name} (来自群: {origin_group})"
            
            return reply
            
        except Exception as e:
            logger.error(f"查询绑定记录失败: {e}")
            return f"❌ 查询失败: {e}"

    async def _cmd_me(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        
        binding = await safe_db_operation(self.bot.db.get_binding, user_id)
        if not binding:
            return "❌ 您还未绑定 VRChat 账号"
        
        vrc_name = binding.get("vrc_display_name", "Unknown")
        vrc_id = binding.get("vrc_user_id", "Unknown")
        origin_group = binding.get("origin_group_id", "Unknown")
        bind_time = binding.get("bind_time", "Unknown")
        
        # 获取QQ信息
        try:
            qq_info = await self.bot.qq_client.get_stranger_info(user_id)
            qq_name = qq_info.get("nickname", str(user_id))
        except Exception:
            qq_name = str(user_id)

        try:
            vrc_user = await self.bot.vrc_client.get_user(vrc_id)
            if vrc_user:
                status = vrc_user.get("status", "Unknown")
                
                status_map = {
                    "active": "在线",
                    "join me": "加入我",
                    "ask me": "询问我",
                    "busy": "忙碌",
                    "offline": "离线"
                }
                status = status_map.get(status, status)
                
                status_desc = vrc_user.get("statusDescription", "")
                bio = vrc_user.get("bio", "暂无简介")
                avatar_url = vrc_user.get("currentAvatarImageUrl") or vrc_user.get("userIcon") or vrc_user.get("profilePicOverride")
                
                # 生成图片
                from src.utils import generate_user_info_image
                temp_dir = "data/temp"
                os.makedirs(temp_dir, exist_ok=True)
                filename = f"me_{user_id}_{int(time.time())}.png"
                output_path = os.path.join(temp_dir, filename)
                abs_output_path = os.path.abspath(output_path)
                
                proxy = self.bot.vrc_config.proxy
                
                await asyncio.to_thread(
                    generate_user_info_image,
                    user_id, qq_name, vrc_name, vrc_id, bio, 
                    abs_output_path, avatar_url, proxy, status,
                    status_desc, bind_time, origin_group
                )
                
                return f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"

        except Exception as e:
            logger.error(f"生成个人信息图片失败: {e}")
        
        # 降级为文本
        return f"您的绑定信息:\nVRChat: {vrc_name} ({vrc_id})\n绑定时间: {bind_time}\n绑定来源群: {origin_group}"

    async def _cmd_admin(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        group_id = context.get("group_id")
        
        if not is_super_admin(user_id, self.bot.global_config.admin_qq):
            return None
        
        if not group_id:
            return "❌ 该指令仅限在群聊中使用"
        
        if not args:
            return "用法: !admin [@某人] - 提升或取消群管理员权限"
        
        import re
        at_match = re.search(r'\[CQ:at,qq=(\d+)\]', args[0])
        if not at_match:
            return "❌ 请@要管理的用户"
        
        target_qq = int(at_match.group(1))
        
        try:
            # 从 NapCat 获取用户角色信息，而不是依赖配置
            member_info = await self.bot.qq_client.get_group_member_info(group_id, target_qq)
            if not member_info:
                return f"❌ 无法获取用户信息: {target_qq}"
                
            current_role = member_info.get('role', 'member')
            
            if current_role in ['admin', 'owner']:
                # 如果是管理员或群主，取消管理员权限
                # 注意：NapCat本身不提供修改群管理员权限的API
                # 我们只能通过配置来管理虚拟的管理员权限
                # 但在新的设计中，我们完全依赖NapCat返回的角色信息
                return f"❌ 无法操作：{target_qq} 当前是群{ '主' if current_role == 'owner' else '管理员' }，需要在QQ群中直接操作"
            else:
                # 如果不是管理员，提示需要在QQ群中直接设置
                return f"❌ 无法操作：需要在QQ群中将 {target_qq} 设置为管理员或群主"

        except Exception as e:
            logger.error(f"检查用户角色失败: {e}")
            return f"❌ 操作失败: {e}"

    async def _cmd_glbind(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        
        if not is_super_admin(user_id, self.bot.global_config.admin_qq):
            return None
            
        if len(args) < 2:
            return "用法: !glbind [QQ号] [VRChat ID/名字]"
            
        try:
            target_qq = int(args[0])
        except ValueError:
            return "❌ QQ号格式不正确"
            
        vrc_query = " ".join(args[1:])
        
        # 查找 VRChat 用户并验证绑定
        try:
            user_info, error = await self.bot.group_handler.validate_vrc_user_for_binding(vrc_query, target_qq)
            if error:
                return error
                
            vrc_id = user_info["id"]
            vrc_name = user_info["displayName"]
            
            # 执行全局绑定 (group_id=None)
            success = await safe_db_operation(self.bot.db.bind_user, target_qq, vrc_id, vrc_name, "manual_global", None)
            
            # 同时添加到全局验证表
            await safe_db_operation(self.bot.db.add_global_verification, target_qq, vrc_id, vrc_name, "admin")
            
            return f"✅ 已全局绑定 QQ {target_qq} 到 VRChat: {vrc_name}" if success else "❌ 数据库操作失败"
            
        except Exception as e:
            logger.error(f"全局绑定失败: {e}")
            return f"❌ 绑定过程出错: {e}"

    async def _cmd_unglbind(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        
        if not is_super_admin(user_id, self.bot.global_config.admin_qq):
            return None
            
        if not args:
            return "用法: !unglbind [QQ号]"
            
        try:
            target_qq = int(args[0])
        except ValueError:
            return "❌ QQ号格式不正确"
            
        try:
            # 首先从全局验证表中删除
            global_verification = await safe_db_operation(self.bot.db.get_global_verification, target_qq)
            if global_verification:
                # 删除全局验证记录
                # 由于没有直接删除全局验证记录的方法，我们直接从数据库删除
                cursor = self.bot.db.conn.cursor()
                cursor.execute("DELETE FROM global_verifications WHERE qq_id = ?", (target_qq,))
                self.bot.db.conn.commit()
            
            # 然后执行全局解绑
            success = await safe_db_operation(self.bot.db.unbind_user_globally, target_qq)
            return f"✅ 已全局解绑 QQ: {target_qq}" if success else f"❌ 解绑失败"
        except Exception as e:
            logger.error(f"全局解绑失败: {e}")
            return f"❌ 解绑过程出错: {e}"

    async def _cmd_unlist(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        # 1. 权限检查: 仅限超级管理员
        user_id = context.get("user_id")
        if not is_super_admin(user_id, self.bot.global_config.admin_qq):
            return None 
        
        # 2. 参数检查
        if not args:
            return "用法: !unlist [QQ群号]"
        
        try:
            target_group_id = int(args[0])
        except ValueError:
            return "❌ 群号格式不正确"
        
        # 3. 检查是否存在绑定
        try:
            vrc_group_id = await safe_db_operation(self.bot.db.get_group_vrc_group_id, target_group_id)
            if not vrc_group_id:
                return f"❌ 群 {target_group_id} 尚未绑定任何 VRChat 群组"
            
            # 4. 执行解绑
            success = await safe_db_operation(self.bot.db.delete_group_vrc_group_id, target_group_id)
            if success:
                return f"✅ 已成功解除群 {target_group_id} 与 VRChat 群组的绑定"
            else:
                return f"❌ 解绑失败: 数据库操作错误"
                
        except Exception as e:
            logger.error(f"解绑群组失败: {e}")
            return f"❌ 解绑失败: {e}"

    async def _cmd_set(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        """处理!set命令，用于设置群组功能开关和参数"""
        user_id = context.get("user_id")
        group_id = context.get("group_id")
        
        # 检查是否在群聊中
        if not group_id:
            return "❌ 此命令仅可在群聊中使用"
        
        # 检查权限
        if not is_admin:
            return "❌ 仅群管理员或机器人超管可使用此命令"
            
        # 调用命令处理器处理设置命令
        return await self.command_handler.handle_set_command(args, context)