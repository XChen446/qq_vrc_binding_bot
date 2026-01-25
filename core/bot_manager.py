import logging
import asyncio
from config.global_config import GlobalConfig
from config.qq_config import QQConfig
from config.vrc_config import VRCConfig
from api.qq.websocket import QQWebSocketManager
from api.qq.client import QQClient
from api.vrc.client import VRCApiClient
from handlers.qq_handler.message_handler import MessageHandler
from handlers.qq_handler.group_handler import GroupHandler
from handlers.vrc_handler.world_handler import WorldHandler
from core.event_router import EventRouter
from core.scheduler import Scheduler
from core.database import get_database

logger = logging.getLogger("BotManager")

class BotManager:
    def __init__(self, config_data):
        self.config_data = config_data
        
        # 1. 初始化配置
        self.global_config = GlobalConfig(config_data)
        self.qq_config = QQConfig(config_data)
        self.vrc_config = VRCConfig(config_data)
        
        # 2. 初始化 API 客户端
        self.ws_manager = QQWebSocketManager(
            self.qq_config.ws_url,
            self.qq_config.token,
            max_retries=self.qq_config.ws_max_retries,
            initial_delay=self.qq_config.ws_initial_delay,
            max_delay=self.qq_config.ws_max_delay
        )
        self.qq_client = QQClient(self.ws_manager)
        self.vrc_client = VRCApiClient(self.vrc_config)
        
        # 3. 初始化数据库
        self.db = get_database(config_data)
        
        # 4. 初始化 Handler
        self.message_handler = MessageHandler(self)
        self.group_handler = GroupHandler(self)
        self.vrc_handler = WorldHandler(self)
        
        # 5. 初始化核心组件
        self.event_router = EventRouter(self)
        self.scheduler = Scheduler(self)
        
        # 绑定消息回调
        self.ws_manager.on_message_callback = self.event_router.dispatch

    async def start(self):
        """启动机器人服务"""
        logger.info("正在启动全异步机器人服务...")
        
        # 验证 VRChat 登录
        if not await self.vrc_client.auth.verify_auth():
            logger.warning("VRChat 验证失败，尝试重新登录...")
            if not await self.vrc_client.auth.login():
                logger.error("VRChat 登录失败，请检查配置。")
        
        # 启动 WebSocket 和 Scheduler
        await asyncio.gather(
            self.ws_manager.connect(),
            self.scheduler.start()
        )

    async def stop(self):
        """停止机器人服务"""
        logger.info("正在停止服务...")
        await self.ws_manager.disconnect()
        await self.vrc_client.close()
