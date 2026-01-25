import time
import logging
import asyncio
import os
from typing import Dict, Any
from utils.image_generator import generate_binding_list_image, generate_user_info_image, generate_query_result_image

logger = logging.getLogger("QQBot.MessageHandler")

class MessageHandler:
    def __init__(self, bot):
        self.bot = bot
        self._user_cooldowns: Dict[int, float] = {}
        self._command_cooldowns: Dict[str, Dict[int, float]] = {}

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
        raw_message = data.get("raw_message", "").strip()
        group_id = data.get("group_id")

        if not raw_message.startswith("!"):
            return

        parts = raw_message.split()
        command = parts[0][1:].lower()
        args = parts[1:]

        # 检查指令是否启用
        if not self._is_command_enabled(command):
            return

        # 检查冷却
        if not self._check_cooldown(command, user_id):
            return
        
        await self._handle_command(command, args, data)

    async def _handle_command(self, command: str, args: list, context: Dict[str, Any]):
        group_id = context.get("group_id")
        user_id = context.get("user_id")
        is_admin = user_id in self.bot.global_config.admin_qq
        
        # 检查权限
        cmd_config = self._get_command_config(command)
        admin_only = cmd_config.get("admin_only", False)
        
        if admin_only and not is_admin:
            return
        
        reply = ""
        if command == "help":
            # 动态生成帮助信息
            help_lines = ["VRChat 机器人指令列表:"]
            
            commands_help = {
                "instances": "查看群组活跃实例 (图片展示)",
                "bind": "[QQ] [VRC ID/名字] - 手动绑定账号",
                "unbind": "[QQ] - 解绑指定 QQ",
                "list": "[QQ群号] - 查看指定群的绑定记录 (私聊使用)",
                "query": "[名字/ID] - 查询绑定记录",
                "search": "[名字/ID] - 搜索 VRChat 用户",
                "me": "查看我的绑定信息"
            }
            
            for cmd, desc in commands_help.items():
                cfg = self._get_command_config(cmd)
                if not cfg.get("enabled", True):
                    continue
                if cfg.get("admin_only", False) and not is_admin:
                    continue
                help_lines.append(f"!{cmd} - {desc}")
                
            help_lines.append("!help - 显示此帮助信息")
            reply = "\n".join(help_lines)
        
        elif command == "instances":
            if not group_id:
                reply = "❌ 该指令仅限在群聊中使用喵~"
            else:
                reply = await self.bot.vrc_handler.handle_instances_command(group_id)

        elif command in ["bind", "unbind", "list", "search", "query"]:
            if command == "bind":
                if len(args) < 2:
                    reply = "用法: !bind [QQ号] [VRChat ID/名字]"
                else:
                    target_qq = int(args[0])
                    vrc_query = " ".join(args[1:])
                    reply = await self.bot.group_handler.manual_bind(target_qq, vrc_query)
            elif command == "unbind":
                if len(args) < 1:
                    reply = "用法: !unbind [QQ号]"
                else:
                    target_qq = int(args[0])
                    success = await asyncio.to_thread(self.bot.db.unbind_user, target_qq)
                    reply = f"✅ 已成功解绑 QQ: {target_qq}" if success else f"❌ 解绑失败，该 QQ 可能未绑定"
            elif command == "list":
                if group_id:
                    reply = "该指令请私聊使用喵~\n用法: !list [QQ群号]"
                else:
                    if not args:
                        reply = "用法: !list [QQ群号]"
                    else:
                        try:
                            group_qq = int(args[0])
                        except ValueError:
                            reply = "❌ 群号格式不正确"
                            return

                        try:
                            member_list = await self.bot.qq_client.get_group_member_list(group_qq)
                            if not member_list:
                                reply = "❌ 无法获取群成员列表，请检查群号是否正确或机器人是否有权限"
                                return
                            
                            qq_ids = [member['user_id'] for member in member_list]
                            bindings = await asyncio.to_thread(self.bot.db.get_bindings_by_qq_list, qq_ids)
                            
                            if not bindings:
                                reply = "该群暂无绑定记录"
                            else:
                                list_limit = self._get_command_config("list").get("max_results", 50)
                                display_bindings = bindings[:list_limit]
                                
                                async def get_info(b):
                                    qq_id = b['qq_id']
                                    try:
                                        info = await self.bot.qq_client.get_stranger_info(qq_id)
                                        qq_name = info.get('nickname', '未知')
                                    except:
                                        qq_name = "未知"
                                        
                                    return {
                                        'qq_id': qq_id,
                                        'qq_name': qq_name,
                                        'vrc_name': b['vrc_display_name'],
                                        'vrc_id': b['vrc_user_id']
                                    }

                                tasks = [get_info(b) for b in display_bindings]
                                results = await asyncio.gather(*tasks)
                                
                                temp_dir = "data/temp"
                                os.makedirs(temp_dir, exist_ok=True)
                                filename = f"bindings_{int(time.time())}.png"
                                output_path = os.path.join(temp_dir, filename)
                                abs_output_path = os.path.abspath(output_path)
                                
                                try:
                                    await asyncio.to_thread(generate_binding_list_image, results, abs_output_path)
                                    reply = f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
                                    if len(bindings) > list_limit:
                                        reply += f"\n(仅显示前 {list_limit} 条，共 {len(bindings)} 条)"
                                except Exception as e:
                                    logger.error(f"生成绑定列表图片失败: {e}")
                                    reply = f"❌ 生成图片失败: {e}"
                        except Exception as e:
                            logger.error(f"查询群绑定记录失败: {e}")
                            reply = f"❌ 查询失败: {e}"
            elif command == "search":
                if not args:
                    reply = "用法: !search [名字/ID]"
                else:
                    query = " ".join(args)
                    users = await self.bot.vrc_client.search_user(query)
                    if not users:
                        reply = "未找到匹配用户"
                    else:
                        reply = "搜索结果:\n" + "\n".join([f"- {u['displayName']} ({u['id']})" for u in users[:5]])
            elif command == "query":
                if not args:
                    reply = "用法: !query [QQ名字/VRChat名字/VRChatID]"
                else:
                    query = " ".join(args)
                    
                    # 获取所有绑定
                    all_bindings = await asyncio.to_thread(self.bot.db.get_all_bindings)
                    
                    results = []
                    
                    # 遍历所有绑定记录进行匹配
                    for binding in all_bindings:
                        match = False
                        
                        # 检查 VRChat ID 匹配
                        if query.lower() in binding['vrc_user_id'].lower():
                            match = True
                        
                        # 检查 VRChat 名字匹配
                        if query.lower() in binding['vrc_display_name'].lower():
                            match = True
                        
                        # 检查 QQ 号匹配
                        if query.isdigit() and str(binding['qq_id']) == query:
                            match = True
                        
                        # 获取 QQ 昵称并匹配
                        try:
                            qq_info = await self.bot.qq_client.get_stranger_info(binding['qq_id'])
                            qq_name = qq_info.get('nickname', '')
                            if query.lower() in qq_name.lower():
                                match = True
                        except:
                            pass
                        
                        if match:
                            results.append(binding)
                    
                    if not results:
                        reply = "未找到匹配的绑定记录"
                    else:
                        processed_results = []
                        for result in results:
                            # 获取 QQ 昵称
                            try:
                                qq_info = await self.bot.qq_client.get_stranger_info(result['qq_id'])
                                qq_name = qq_info.get('nickname', '未知')
                            except:
                                qq_name = "未知"
                            
                            result['qq_name'] = qq_name
                            processed_results.append(result)
                        
                        # 限制显示数量，防止图片过大
                        display_limit = self._get_command_config("query").get("max_results", 50)
                        display_results = processed_results[:display_limit]
                        
                        # 生成图片
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
                        except Exception as e:
                            logger.error(f"生成查询结果图片失败: {e}")
                            reply = f"❌ 生成图片失败: {e}"

        elif command == "me":
            binding = await asyncio.to_thread(self.bot.db.get_binding, user_id)
            if not binding:
                reply = "❌ 您还没有绑定 VRChat 账号"
            else:
                try:
                    # 获取 QQ 昵称
                    qq_info = await self.bot.qq_client.get_stranger_info(user_id)
                    qq_name = qq_info.get('nickname', '未知')
                    
                    # 获取 VRChat 用户详细信息
                    vrc_id = binding['vrc_user_id']
                    vrc_user = await self.bot.vrc_client.get_user(vrc_id)
                    
                    if vrc_user:
                        vrc_name = vrc_user.get('displayName', '未知')
                        bio = vrc_user.get('bio', '暂无简介') or '暂无简介'
                        avatar_url = vrc_user.get('currentAvatarThumbnailImageUrl')
                    else:
                        vrc_name = binding['vrc_display_name']
                        bio = '无法获取简介'
                        avatar_url = None
                    
                    # 生成图片
                    temp_dir = "data/temp"
                    os.makedirs(temp_dir, exist_ok=True)
                    filename = f"me_{user_id}_{int(time.time())}.png"
                    output_path = os.path.join(temp_dir, filename)
                    abs_output_path = os.path.abspath(output_path)
                    
                    try:
                        proxy = self.bot.global_config.vrc_proxy
                        await asyncio.to_thread(
                            generate_user_info_image,
                            user_id,
                            qq_name,
                            vrc_name,
                            vrc_id,
                            bio,
                            abs_output_path,
                            avatar_url,
                            proxy
                        )
                        reply = f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
                    except Exception as e:
                        logger.error(f"生成用户信息图片失败: {e}")
                        reply = f"❌ 生成图片失败: {e}"
                except Exception as e:
                    logger.error(f"获取用户信息失败: {e}")
                    reply = f"❌ 获取信息失败: {e}"

        if reply:
            if group_id:
                await self.bot.qq_client.send_group_msg(group_id, reply)
            else:
                await self.bot.qq_client.send_private_msg(user_id, reply)
