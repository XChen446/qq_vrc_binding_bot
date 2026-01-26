import os
import time
import logging
from typing import Optional, List, Dict, Any
from utils.image_generator import generate_instance_image

logger = logging.getLogger("VRChatAPI.WorldHandler")

class WorldHandler:
    TEMP_DIR = "data/temp"

    def __init__(self, bot):
        self.bot = bot
        os.makedirs(self.TEMP_DIR, exist_ok=True)

    async def handle_instances_command(self, group_id: int) -> Optional[str]:
        """处理查询实例指令"""
        vrc_group_id = self._get_vrc_group_id()
        if not vrc_group_id:
            return "❌ 机器人未配置 VRChat 群组 ID喵~"

        try:
            instances = await self.bot.vrc_client.get_group_instances(vrc_group_id)
            if instances is None:
                return "❌ 获取实例列表失败喵~"
            
            if not instances:
                return " 当前群组没有任何活跃实例喵~"

            return await self._generate_and_send_image(group_id, instances)

        except Exception as e:
            logger.error(f"处理实例查询指令失败: {e}", exc_info=True)
            return f"❌ 发生内部错误喵: {str(e)}"

    def _get_vrc_group_id(self) -> Optional[str]:
        return self.bot.vrc_config.verification.get("group_id")

    async def _generate_and_send_image(self, group_id: int, instances: List[Dict[str, Any]]) -> None:
        # 按人数排序
        instances.sort(key=self._get_user_count, reverse=True)

        filename = f"instances_{group_id}_{int(time.time())}.png"
        output_path = os.path.join(self.TEMP_DIR, filename)
        abs_output_path = os.path.abspath(output_path)
        
        proxy = self.bot.vrc_config.proxy
        # 在线程池中生成图片
        await self.bot.loop.run_in_executor(
            None, 
            generate_instance_image, 
            instances, 
            abs_output_path, 
            proxy
        )

        image_msg = f"[CQ:image,file=file:///{abs_output_path.replace('\\', '/')}]"
        await self.bot.qq_client.send_group_msg(group_id, image_msg)

    @staticmethod
    def _get_user_count(inst: Dict[str, Any]) -> int:
        return inst.get("n_users") or inst.get("memberCount") or 0
