#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQ到VRChat双向绑定机器人
主入口文件
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.app import QQVRCBindingApp
from loguru import logger


async def main():
    """主函数"""
    try:
        # 检查命令行参数
        cli_mode = '--cli' in sys.argv
        config_file = None
        
        # 解析命令行参数
        for i, arg in enumerate(sys.argv):
            if arg == '--config' and i + 1 < len(sys.argv):
                config_file = sys.argv[i + 1]
                break
        
        # 使用默认配置文件
        if not config_file:
            config_file = "config/config.yaml"
        
        # 创建应用实例
        app = QQVRCBindingApp(config_file=config_file)
        
        # 初始化
        await app.initialize()
        
        # 根据模式运行
        if cli_mode:
            logger.info("运行CLI模式")
            await app.run_cli()
        else:
            logger.info("运行服务模式")
            await app.start()
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭应用...")
    except Exception as e:
        logger.exception(f"应用运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行主函数
    asyncio.run(main())