"""
机器人核心管理器 (BotManager)
"""

import logging
import asyncio
from typing import Dict, Any

from src.core.global_config import GlobalConfig
from src.core.qq_config import QQConfig
from src.core.vrc_config import VRCConfig
from src.core.message_config import MessageConfig
from src.api.qq.websocket import QQWebSocketManager
from src.api.qq.client import QQClient
from src.api.vrc.client import VRCApiClient
from src.core.event_router import EventRouter
from src.core.scheduler import Scheduler
from src.core.database import get_database

logger = logging.getLogger("BotManager")

class BotManager:
    def __init__(self, config_data: Dict[str, Any], config_path: str = None):
        self.config_data = config_data
        self.config_path = config_path
        self._is_running = False
        
        # 1. 初始化配置
        self._init_configs(config_data)
        
        # 2. 初始化消息配置
        self._init_message_config()
        
        # 3. 初始化核心组件 (API, DB)
        self._init_components()
        
        # 4. 延迟初始化处理器，避免循环导入
        self._init_handlers()
        
        # 5. 绑定事件回调
        self.ws_manager.on_message_callback = self.event_router.dispatch

    def _init_configs(self, config_data: Dict[str, Any]):
        """初始化配置对象"""
        self.global_config = GlobalConfig(config_data)
        self.qq_config = QQConfig(config_data)
        self.vrc_config = VRCConfig(config_data)
    
    def _init_message_config(self):
        """初始化消息配置对象"""
        self.message_config = MessageConfig()

    def _init_components(self):
        """初始化各功能组件"""
        # API 客户端
        self.ws_manager = QQWebSocketManager(
            self.qq_config.ws_url,
            self.qq_config.token,
            max_retries=self.qq_config.ws_max_retries,
            initial_delay=self.qq_config.ws_initial_delay,
            max_delay=self.qq_config.ws_max_delay
        )
        self.qq_client = QQClient(self.ws_manager)
        self.vrc_client = VRCApiClient(self.vrc_config)
        
        # 数据库
        self.db = get_database(self.config_data)
        
        # 核心调度
        self.event_router = EventRouter(self)
        self.scheduler = Scheduler(self)

    def _init_handlers(self):
        """延迟初始化处理器，避免循环导入"""
        from src.handlers.qq_handler.message_handler import MessageHandler
        from src.handlers.qq_handler.group_handler import GroupHandler
        from src.handlers.vrc_handler.world_handler import WorldHandler
        
        self.message_handler = MessageHandler(self, config_path=self.config_path)
        self.group_handler = GroupHandler(self)
        self.vrc_handler = WorldHandler(self)

    async def start(self):
        """启动机器人服务"""
        if self._is_running:
            logger.warning("Bot 已经在运行中")
            return
            
        logger.info("正在启动全异步机器人服务...")
        logger.debug(f"配置数据: 全局配置={bool(self.global_config)}, QQ配置={bool(self.qq_config)}, VRChat配置={bool(self.vrc_config)}")
        self._is_running = True
        
        try:
            # 1. 验证 VRChat 登录 (失败尝试重登)
            await self._ensure_vrc_auth()
            
            # 2. 启动 WebSocket 和 Scheduler
            await asyncio.gather(
                self.ws_manager.connect(),
                self.scheduler.start()
            )
        except Exception as e:
            logger.critical(f"Bot 启动失败: {e}", exc_info=True)
            logger.debug(f"启动失败时的运行状态: {self._is_running}")
            await self.stop()

    async def stop(self):
        """停止机器人服务"""
        logger.info(f"正在停止服务... 当前运行状态: {self._is_running}")
        self._is_running = False
        
        # 优雅关闭各组件
        await self.scheduler.stop()
        await self.ws_manager.disconnect()
        await self.vrc_client.close()
        logger.info(f"服务已停止 当前运行状态: {self._is_running}")

    async def _ensure_vrc_auth(self):
        """确保 VRChat 认证有效"""
        logger.info("检查 VRChat 认证状态...")
        logger.debug(f"当前认证状态: {await self.vrc_client.auth.verify_auth()}")
        if not await self.vrc_client.auth.verify_auth():
            logger.warning("VRChat 验证失败，尝试重新登录...")
            if not await self.vrc_client.auth.login():
                logger.error("VRChat 登录失败，请检查配置。部分功能可能不可用。")
            else:
                # 获取登录后的用户信息并显示用户名
                try:
                    current_user = await self.vrc_client.auth.authentication_api.get_current_user(async_req=True)
                    if current_user and hasattr(current_user, 'display_name'):
                        logger.info(f"VRChat 重新登录成功 用户: {current_user.display_name}")
                    else:
                        logger.info("VRChat 重新登录成功")
                except Exception:
                    logger.info("VRChat 重新登录成功")
        else:
            # 获取当前用户信息并显示用户名
            try:
                current_user = await self.vrc_client.auth.authentication_api.get_current_user(async_req=True)
                if current_user and hasattr(current_user, 'display_name'):
                    logger.info(f"VRChat 认证有效 用户: {current_user.display_name}")
                else:
                    logger.info("VRChat 认证有效")
            except Exception:
                logger.info("VRChat 认证有效")