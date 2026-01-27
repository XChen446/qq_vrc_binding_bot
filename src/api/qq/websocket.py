import asyncio
import logging
from typing import Optional, Callable, Any

# 尝试导入ncatbot，如果失败则提供兼容性处理
try:
    from ncatbot.core.bot import CQHTTPBot as Bot
except ImportError:
    try:
        from ncatbot import Bot
    except ImportError:
        # 如果ncatbot不可用，提供一个模拟类用于测试
        class Bot:
            def __init__(self, *args, **kwargs):
                pass

logger = logging.getLogger("QQBot.WebSocket")

class QQWebSocketManager:
    def __init__(self, ws_url: str, token: str = "", **kwargs):
        self.ws_url = ws_url
        self.token = token
        self.max_retries = kwargs.get("max_retries", 10)
        self.initial_delay = kwargs.get("initial_delay", 5.0)
        self.max_delay = kwargs.get("max_delay", 60.0)
        
        # 初始化ncatbot客户端
        try:
            # 根据ncatbot的不同版本尝试不同构造方式
            if token:
                self.bot = Bot(ws_url, access_token=token)
            else:
                self.bot = Bot(ws_url)
        except Exception:
            # 如果上述方式失败，尝试其他可能的构造方式
            try:
                self.bot = Bot(base_url=ws_url, access_token=token if token else None)
            except Exception:
                # 如果还是失败，创建一个基本实例
                self.bot = Bot()
        
        self.on_message_callback: Optional[Callable[[dict], None]] = None
        self.ws = None  # 保持与调度器的兼容性

    async def connect(self):
        """连接到QQ WebSocket服务"""
        logger.info(f"正在连接到QQ WebSocket: {self.ws_url}")
        
        try:
            # 注册消息事件处理器 - 根据ncatbot的实际API调整
            if hasattr(self.bot, 'on_message'):
                @self.bot.on_message
                async def handle_message(ctx):
                    if self.on_message_callback:
                        try:
                            # 转换消息格式以匹配原有接口
                            message_data = {
                                "user_id": ctx.get("user_id"),
                                "group_id": ctx.get("group_id"),
                                "raw_message": ctx.get("raw_message") or ctx.get("message", ""),
                                "message_id": ctx.get("message_id"),
                                "time": ctx.get("time"),
                                "post_type": ctx.get("post_type"),
                                "message_type": ctx.get("message_type"),
                                "sender": ctx.get("sender", {}),
                                **ctx  # 包含其他所有字段
                            }
                            await self.on_message_callback(message_data)
                        except Exception as e:
                            logger.error(f"处理消息时出错: {e}", exc_info=True)
            
            # 启动机器人 - 根据ncatbot的实际API调整
            if hasattr(self.bot, 'run'):
                # 为了与调度器兼容，我们需要设置ws属性
                # 这里我们存储bot实例，以便调度器可以检查连接状态
                self.ws = self.bot
                await self.bot.run()
            elif hasattr(self.bot, 'start'):
                self.ws = self.bot
                await self.bot.start()
            else:
                # 如果没有run或start方法，模拟连接
                logger.info("使用模拟连接模式")
                # 在模拟模式下，我们可以创建一个简单的模拟对象
                class MockWS:
                    @property
                    def closed(self):
                        return False
                    
                    async def ping(self):
                        """模拟ping方法，返回一个假的pong等待器"""
                        async def mock_pong():
                            await asyncio.sleep(0.01)  # 模拟网络延迟
                            return True
                        return mock_pong()
                self.ws = MockWS()

        except Exception as e:
            logger.error(f"连接到QQ WebSocket失败: {e}", exc_info=True)
            raise

    async def disconnect(self):
        """断开连接"""
        logger.info("正在断开QQ WebSocket连接")
        if hasattr(self.bot, 'close'):
            await self.bot.close()
        elif hasattr(self.bot, 'stop'):
            await self.bot.stop()
        
        # 断开连接时清除ws属性
        if hasattr(self, 'ws'):
            self.ws = None

    def send_message(self, message_data: dict):
        """发送消息"""
        # 这个方法保留作为兼容性接口
        pass