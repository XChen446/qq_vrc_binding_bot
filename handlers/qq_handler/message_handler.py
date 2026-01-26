import time
import logging
import asyncio
import os
from typing import Dict, Any, List
from utils.image_generator import generate_binding_list_image, generate_user_info_image, generate_query_result_image

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
    def __init__(self, bot):
        self.bot = bot
        self._user_cooldowns: Dict[int, float] = {}
        self._command_cooldowns: Dict[str, Dict[int, float]] = {}
        
        # 注册指令处理函数
        self._command_handlers = {
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
            "me": self._cmd_me
        }

    def _get_command_config(self, command: str) -> Dict[str, Any]:
        return self.bot.global_config.commands.get(command, {})

    def _is_command_enabled(self, command: str) -> bool:
        config = self._get_command_config(command)
        return config.get("enabled", True)

    def _check_cooldown(self, command: str, user_id: int) -> bool:
        config = self._get_command_config(command)
        cooldown = config.get("cooldown", 3)
        
        now = time.time()
        
        # 检查全局冷却
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
        
        # 消息来源描述
        source_desc = f"Group({group_id})" if group_id else f"Private({user_id})"

        if not raw_message.startswith("!"):
            return

        parts = raw_message.split()
        command = parts[0][1:].lower()
        args = parts[1:]
        
        logger.info(f"收到指令: {command} | Args: {args} | User: {user_id} | Source: {source_desc}")

        # 检查指令是否启用
        if not self._is_command_enabled(command):
            logger.debug(f"指令未启用: {command}")
            return

        # 检查冷却
        if not self._check_cooldown(command, user_id):
            logger.debug(f"指令冷却中: {command} (User: {user_id})")
            return
        
        # 调用指令处理
        try:
            result = await self._handle_command(command, args, data)
            # 如果处理函数有返回值（通常是回复消息），记录结果
            if result:
                # 截断过长的回复日志
                reply_log = str(result)
                if len(reply_log) > 100:
                    reply_log = reply_log[:100] + "..."
                logger.info(f"指令处理完成: {command} | Reply: {reply_log}")
            else:
                logger.info(f"指令处理完成: {command} | No Reply")
        except Exception as e:
            logger.error(f"指令处理异常: {command} | Error: {e}")
            await self._reply(data, f"❌ 指令执行出错: {e}")

    async def _handle_command(self, command: str, args: list, context: Dict[str, Any]):
        user_id = context.get("user_id")
        is_admin = user_id in self.bot.global_config.admin_qq
        
        # 检查权限
        cmd_config = self._get_command_config(command)
        admin_only = cmd_config.get("admin_only", False)
        
        if admin_only and not is_admin:
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
        """快捷回复"""
        group_id = context.get("group_id")
        user_id = context.get("user_id")
        
        if group_id:
            await self.bot.qq_client.send_group_msg(group_id, message)
        else:
            await self.bot.qq_client.send_private_msg(user_id, message)
        
        return message # 返回消息以便上层记录日志

    # === Command Handlers ===

    async def _cmd_help(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        # 获取用户绑定状态
        binding = await asyncio.to_thread(self.bot.db.get_binding, user_id)

        help_lines = ["VRChat 机器人指令列表:"]
        commands_help = {
            "instances": "查看群组活跃实例 (图片展示)",
            "bind": "[QQ] [VRC ID/名字] - 手动绑定账号",
            "unbind": "[QQ] - 解绑指定 QQ",
            "list": "[QQ群号] or [global] - 查看指定群或全局的绑定记录 (私聊使用)",
            "query": "[名字/ID] - 查询绑定记录",
            "search": "[名字/ID] - 搜索 VRChat 用户",
            "me": "查看我的绑定信息",
            "verify": "验证 VRChat 账号归属",
            "unbound": "[QQ群号] - 查询群内未绑定的成员 (仅限管理，私聊使用)",
            "code": "查询当前的验证码"
        }
        
        for cmd, desc in commands_help.items():
            cfg = self._get_command_config(cmd)
            if not cfg.get("enabled", True):
                continue
            if cfg.get("admin_only", False) and not is_admin:
                continue
            
            # 特殊规则：unbound 仅限管理员可见
            if cmd == "unbound" and not is_admin:
                continue

            # 如果已绑定，隐藏 verify 和 code 指令
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

    async def _cmd_code(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        binding = await asyncio.to_thread(self.bot.db.get_binding, user_id)
        if binding:
            return f"✅ 您已绑定 VRChat 账号 ({binding['vrc_display_name']})。"
        
        verification = await asyncio.to_thread(self.bot.db.get_verification, user_id)
        if verification:
            try:
                created_ts = float(verification.get("created_at"))
            except:
                created_ts = time.time()
            
            expiry_seconds = self.bot.vrc_config.verification.get("code_expiry", 300)
            elapsed = time.time() - created_ts
            remaining = int(expiry_seconds - elapsed)
            if remaining < 0: remaining = 0

            return f"您的验证码是: {verification['code']}\n有效时间剩余: {remaining}秒\n请将 VRChat 状态描述修改为此验证码，然后发送 !verify"
        else:
            return "❌ 您当前没有待验证的请求。"

    async def _cmd_verify(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        group_id = context.get("group_id")
        
        binding = await asyncio.to_thread(self.bot.db.get_binding, user_id)
        if binding:
            return f"✅ 您已绑定 VRChat 账号 ({binding['vrc_display_name']})，无需再次验证。"
        
        verification = await asyncio.to_thread(self.bot.db.get_verification, user_id)
        if not verification:
            return "❌ 您当前没有待验证的请求。如果您刚进群，请检查是否已绑定 VRChat 账号。"
            
        vrc_id = verification["vrc_user_id"]
        code = verification["code"]
        vrc_name = verification["vrc_display_name"]

        try:
            created_ts = float(verification.get("created_at"))
        except:
            created_ts = time.time()

        expiry_seconds = self.bot.vrc_config.verification.get("code_expiry", 300)
        if time.time() - created_ts > expiry_seconds:
            await asyncio.to_thread(self.bot.db.delete_verification, user_id)
            return "❌ 验证码已过期，请联系管理员重新申请或重新入群。"
        
        try:
            vrc_user = await self.bot.vrc_client.get_user(vrc_id)
            if not vrc_user:
                return "❌ 无法获取 VRChat 用户信息，请稍后再试。"
            
            status_desc = vrc_user.get("statusDescription", "")
            if code in status_desc:
                # 验证成功
                await asyncio.to_thread(self.bot.db.bind_user, user_id, vrc_id, vrc_name, "verified", group_id)
                await asyncio.to_thread(self.bot.db.delete_verification, user_id)
                
                reply = f"✅ 验证成功！已绑定 VRChat 账号: {vrc_name}"
                
                # 后续操作
                if group_id:
                    if self.bot.vrc_config.verification.get("auto_rename"):
                        try:
                            await self.bot.qq_client.set_group_card(group_id, user_id, vrc_name)
                        except Exception as e:
                            logger.warning(f"改名失败: {e}")
                    
                    if self.bot.vrc_config.verification.get("auto_assign_role"):
                        vrc_group_id = self.bot.vrc_config.verification.get("group_id")
                        target_role_id = self.bot.vrc_config.verification.get("target_role_id")
                        if vrc_group_id and target_role_id:
                            try:
                                await self.bot.vrc_client.add_group_role(vrc_group_id, vrc_id, target_role_id)
                            except Exception as e:
                                logger.warning(f"分配角色失败: {e}")

                    if self.bot.global_config.enable_welcome:
                        welcome_tpl = self.bot.global_config.templates.get("welcome", "")
                        if welcome_tpl:
                            welcome_msg = welcome_tpl.format(display_name=vrc_name, user_id=user_id)
                            reply += "\n" + welcome_msg
                return reply
            else:
                return f"❌ 验证失败。\n要求状态描述包含: {code}\n当前状态描述: {status_desc or '(空)'}\n请修改后再次输入 !verify"
        except Exception as e:
            logger.error(f"验证过程出错: {e}")
            return f"❌ 验证过程出错: {e}"

    async def _cmd_bind(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        if len(args) < 2:
            return "用法: !bind [QQ号] [VRChat ID/名字]"
        
        target_qq = int(args[0])
        vrc_query = " ".join(args[1:])
        group_id = context.get("group_id")
        return await self.bot.group_handler.manual_bind(target_qq, vrc_query, group_id)

    async def _cmd_unbind(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        if len(args) < 1:
            return "用法: !unbind [QQ号]"
        
        target_qq = int(args[0])
        group_id = context.get("group_id")
        user_id = context.get("user_id")

        if group_id:
            # 群内解绑：检查发送者权限 (超管或群管)
            try:
                sender_info = await self.bot.qq_client.get_group_member_info(group_id, user_id)
                role = sender_info.get("role", "member")
                is_group_admin = role in ["owner", "admin"]
            except:
                is_group_admin = False
            
            if not is_admin and not is_group_admin:
                 return "❌ 只有群管理员或超级管理员可以使用此指令"
            
            # 解绑本群
            success = await asyncio.to_thread(self.bot.db.unbind_user_from_group, group_id, target_qq)
            return f"✅ 已从本群解绑 QQ: {target_qq}" if success else f"❌ 解绑失败，该用户可能未绑定或已解绑"
        else:
            # 私聊：仅限超管
            if not is_admin:
                return "❌ 只有超级管理员可以使用此指令"
            
            # 全局解绑
            success = await asyncio.to_thread(self.bot.db.unbind_user_globally, target_qq)
            return f"✅ 已全局解绑 QQ: {target_qq}" if success else f"❌ 解绑失败"

    async def _cmd_list(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        group_id = context.get("group_id")
        if group_id:
            return "该指令请私聊使用喵~\n用法: !list [QQ群号] 或 !list global"
        
        if not args:
            return "用法: !list [QQ群号] 或 !list global"
        
        if args[0] == "global":
            if not is_admin:
                return "❌ 只有超级管理员可以使用此指令"
            
            try:
                bindings = await asyncio.to_thread(self.bot.db.get_all_bindings)
                if not bindings:
                    return "暂无任何绑定记录"
                
                # 按 origin_group_id 排序
                bindings.sort(key=lambda x: (x.get('origin_group_id') or 0))
                
                list_limit = self._get_command_config("list").get("max_results", 50)
                display_bindings = bindings[:list_limit]
                
                results = await self._fetch_qq_names(display_bindings)
                
                return await _generate_list_image(results, len(bindings) > list_limit, len(bindings), list_limit, is_global=True)

            except Exception as e:
                logger.error(f"查询全局绑定记录失败: {e}")
                return f"❌ 查询失败: {e}"
        else:
            try:
                target_group_qq = int(args[0])
            except ValueError:
                return "❌ 群号格式不正确"

            try:
                bindings = await asyncio.to_thread(self.bot.db.get_group_bindings, target_group_qq)
                if not bindings:
                    return "该群暂无绑定记录"
                
                list_limit = self._get_command_config("list").get("max_results", 50)
                display_bindings = bindings[:list_limit]
                
                results = await self._fetch_qq_names(display_bindings)
                
                return await _generate_list_image(results, len(bindings) > list_limit, len(bindings), list_limit)

            except Exception as e:
                logger.error(f"查询绑定记录失败: {e}")
                return f"❌ 查询失败: {e}"

    async def _fetch_qq_names(self, bindings: List[Dict]) -> List[Dict]:
        async def get_info(b):
            qq_id = b['qq_id']
            try:
                info = await self.bot.qq_client.get_stranger_info(qq_id)
                qq_name = info.get('nickname', '未知')
            except:
                qq_name = "未知"
            
            result = {
                'qq_id': qq_id,
                'qq_name': qq_name,
                'vrc_name': b['vrc_display_name'],
                'vrc_id': b['vrc_user_id']
            }
            if 'origin_group_id' in b:
                result['origin_group_id'] = b['origin_group_id']
            return result

        tasks = [get_info(b) for b in bindings]
        return await asyncio.gather(*tasks)

    async def _cmd_unbound(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        group_id = context.get("group_id")
        if group_id:
            return "该指令请私聊使用喵~\n用法: !unbound [QQ群号]"
        if not is_admin:
            return "❌ 只有管理员可以使用此指令喵~"
        if not args:
            return "用法: !unbound [QQ群号]"
        
        try:
            target_group_id = int(args[0])
            member_list = await self.bot.qq_client.get_group_member_list(target_group_id)
            if not member_list:
                return "❌ 无法获取群成员列表，请检查群号是否正确或机器人是否有权限"
            
            group_bindings = await asyncio.to_thread(self.bot.db.get_group_bindings, target_group_id)
            bound_qq_ids = {str(b['qq_id']) for b in group_bindings}
            
            unbound_members = []
            for member in member_list:
                if str(member['user_id']) not in bound_qq_ids:
                    unbound_members.append(member)
            
            if not unbound_members:
                return "✅ 本群所有成员都已绑定 VRChat 账号！"
            
            count = len(unbound_members)
            reply = f"📋 群 {target_group_id} 共有 {count} 位成员未绑定 VRChat 账号：\n"
            
            limit = 20
            for m in unbound_members[:limit]:
                nickname = m.get('card') or m.get('nickname') or str(m['user_id'])
                reply += f"- {nickname} ({m['user_id']})\n"
            
            if count > limit:
                reply += f"\n...还有 {count - limit} 位成员"
            return reply
        except ValueError:
            return "❌ 群号格式不正确"
        except Exception as e:
            logger.error(f"查询未绑定成员失败: {e}")
            return f"❌ 查询失败: {e}"

    async def _cmd_search(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        if not args:
            return "用法: !search [名字/ID]"
        
        query = " ".join(args)
        users = await self.bot.vrc_client.search_user(query)
        if not users:
            return "未找到匹配用户"
        
        return "搜索结果:\n" + "\n".join([f"- {u['displayName']} ({u['id']})" for u in users[:5]])

    async def _cmd_query(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        if not args:
            return "用法: !query [QQ名字/VRChat名字/VRChatID]"
        
        query = " ".join(args)
        try:
            results = await asyncio.to_thread(self.bot.db.search_global_bindings, query)
        except Exception as e:
            logger.error(f"全局搜索失败: {e}")
            return f"❌ 搜索失败: {e}"

        if not results:
            return "未找到匹配的绑定记录"

        processed_results = []
        for result in results:
            try:
                qq_info = await self.bot.qq_client.get_stranger_info(result['qq_id'])
                qq_name = qq_info.get('nickname', '未知')
            except:
                qq_name = "未知"
            result['qq_name'] = qq_name
            processed_results.append(result)
        
        display_limit = self._get_command_config("query").get("max_results", 50)
        display_results = processed_results[:display_limit]
        
        temp_dir = "data/temp"
        os.makedirs(temp_dir, exist_ok=True)
        filename = f"query_{int(time.time())}.png"
        output_path = os.path.join(temp_dir, filename)
        abs_output_path = os.path.abspath(output_path)
        
        try:
            await asyncio.to_thread(generate_query_result_image, display_results, abs_output_path)
            reply = f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
            if len(results) > display_limit:
                reply += f"\n(仅显示前 {display_limit} 条，共 {len(results)} 条)"
            return reply
        except Exception as e:
            logger.error(f"生成查询结果图片失败: {e}")
            return f"❌ 生成图片失败: {e}"

    async def _cmd_me(self, args: list, context: Dict[str, Any], is_admin: bool) -> str:
        user_id = context.get("user_id")
        binding = await asyncio.to_thread(self.bot.db.get_binding, user_id)
        if not binding:
            return "❌ 您还没有绑定 VRChat 账号"
        
        try:
            qq_info = await self.bot.qq_client.get_stranger_info(user_id)
            qq_name = qq_info.get('nickname', '未知')
            
            vrc_id = binding['vrc_user_id']
            vrc_user = await self.bot.vrc_client.get_user(vrc_id)
            
            if vrc_user:
                vrc_name = vrc_user.get('displayName', '未知')
                bio = vrc_user.get('bio', '暂无简介') or '暂无简介'
                avatar_url = vrc_user.get('currentAvatarThumbnailImageUrl')
                
                # 获取状态
                status = vrc_user.get('status', 'offline')
                status_desc = vrc_user.get('statusDescription', '')
                
                status_map = {
                    'active': '在线',
                    'join me': '加入我',
                    'busy': '忙碌',
                    'offline': '离线'
                }
                status_text = status_map.get(status, status)
                
                # 如果有状态描述，也显示出来（截断一下防止过长）
                if status_desc:
                    # 移除换行符
                    status_desc = status_desc.replace('\n', ' ')
                    if len(status_desc) > 10:
                        status_desc = status_desc[:10] + '...'
                    status_text += f" - {status_desc}"
                
            else:
                vrc_name = binding['vrc_display_name']
                bio = '无法获取简介'
                avatar_url = None
                status_text = "未知状态"
            
            temp_dir = "data/temp"
            os.makedirs(temp_dir, exist_ok=True)
            filename = f"me_{user_id}_{int(time.time())}.png"
            output_path = os.path.join(temp_dir, filename)
            abs_output_path = os.path.abspath(output_path)
            
            proxy = self.bot.global_config.vrchat.get("proxy")
            await asyncio.to_thread(
                generate_user_info_image,
                user_id,
                qq_name,
                vrc_name,
                vrc_id,
                bio,
                abs_output_path,
                avatar_url,
                proxy,
                status_text
            )
            return f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return f"❌ 获取信息失败: {e}"
