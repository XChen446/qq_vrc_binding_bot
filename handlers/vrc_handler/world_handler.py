import os
import time
import logging
from utils.image_generator import generate_instance_image

logger = logging.getLogger("VRChatBot.WorldHandler")

class WorldHandler:
    def __init__(self, bot):
        self.bot = bot
        self.temp_dir = "data/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    async def handle_instances_command(self, group_id: int):
        vrc_group_id = self.bot.vrc_config.verification.get("group_id")
        if not vrc_group_id:
            return "❌ 机器人未配置 VRChat 群组 ID喵~"

        try:
            instances = await self.bot.vrc_client.get_group_instances(vrc_group_id)
            if instances is None:
                return "❌ 获取实例列表失败喵~"
            
            if not instances:
                return "📭 当前群组没有任何活跃实例喵~"

            def get_user_count(inst):
                return inst.get("n_users") or inst.get("memberCount") or 0
            
            instances.sort(key=get_user_count, reverse=True)

            filename = f"instances_{group_id}_{int(time.time())}.png"
            output_path = os.path.join(self.temp_dir, filename)
            abs_output_path = os.path.abspath(output_path)
            
            proxy = self.bot.vrc_config.proxy
            generate_instance_image(instances, abs_output_path, proxy=proxy)

            image_msg = f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
            await self.bot.qq_client.send_group_msg(group_id, image_msg)
            return None

        except Exception as e:
            logger.error(f"处理实例查询指令失败: {e}")
            return f"❌ 发生内部错误喵: {str(e)}"
