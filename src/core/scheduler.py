import asyncio
import logging
from typing import List

logger = logging.getLogger("QQBot.Scheduler")

class Scheduler:
    def __init__(self, bot):
        self.bot = bot
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._cleanup_jobs: List[any] = []

    def register_cleanup_job(self, job):
        """注册定时清理任务"""
        self._cleanup_jobs.append(job)

    async def start(self):
        """启动所有定时任务"""
        self._running = True
        logger.info("正在启动定时任务调度器...")
        
        self._tasks.append(asyncio.create_task(self.monitor_connection()))
        self._tasks.append(asyncio.create_task(self.cleanup_task()))
        self._tasks.append(asyncio.create_task(self.verification_expiry_task()))
        
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            logger.info("调度器任务已取消")
        except Exception as e:
            logger.error(f"调度器运行异常: {e}")

    async def stop(self):
        """停止所有任务"""
        self._running = False
        logger.info("正在停止定时任务调度器...")
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # 等待任务取消
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def monitor_connection(self):
        """检查 WebSocket 连接状态并发送心跳"""
        logger.info("启动连接监控任务")
        while self._running:
            await asyncio.sleep(30)
            
            ws_manager = self.bot.ws_manager
            if not ws_manager or ws_manager.ws is None:
                continue
                
            try:
                # 状态检查
                is_closed = False
                if hasattr(ws_manager.ws, 'closed'):
                    is_closed = ws_manager.ws.closed
                elif hasattr(ws_manager.ws, 'state'):
                    # aiohttp 状态 3 为 CLOSED
                    is_closed = getattr(ws_manager.ws.state, 'value', 0) == 3
                
                if is_closed:
                    logger.warning("检测到 WebSocket 连接已关闭")
                    continue

                # 发送心跳
                pong_waiter = await ws_manager.ws.ping()
                await asyncio.wait_for(pong_waiter, timeout=10)
                
            except asyncio.TimeoutError:
                logger.warning("WebSocket 心跳超时，连接可能已断开")
            except Exception as e:
                logger.error(f"心跳检测异常: {e}")

    async def verification_expiry_task(self):
        """定期检查并标记过期验证码"""
        logger.info("启动验证码过期检查任务")
        while self._running:
            try:
                # 获取配置的过期时间
                expiry = 300
                if self.bot and self.bot.vrc_config:
                    expiry = self.bot.vrc_config.verification.get("code_expiry", 300)
                
                # 执行清理
                if self.bot and self.bot.db:
                    count = await asyncio.to_thread(self.bot.db.expire_outdated_verifications, expiry)
                    if count > 0:
                        logger.info(f"已自动标记 {count} 个过期验证记录")
            except Exception as e:
                logger.error(f"验证码过期检查任务出错: {e}")
            
            # 每10秒检查一次
            await asyncio.sleep(10)

    async def cleanup_task(self):
        """定期清理任务"""
        logger.info("启动定期清理任务")
        while self._running:
            await asyncio.sleep(3600) # 每小时执行一次
            
            logger.info("开始执行定时清理任务...")
            
            # 执行注册的清理任务
            for job in self._cleanup_jobs:
                try:
                    await job()
                except Exception as e:
                    logger.error(f"清理任务执行出错: {e}")
            
            pass
