import argparse
import os
import asyncio
import logging
import sys
import json

# 确保能找到项目模块
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from utils.logger import setup_logger
from config.global_config import load_all_config
from core.bot_manager import BotManager

async def async_main():
    parser = argparse.ArgumentParser(description="VRChat QQ 绑定机器人 (重构版)")
    parser.add_argument("--config", default="config/config.json", help="配置文件路径")
    args = parser.parse_args()

    # 1. 加载配置
    config_path = args.config
    
    # 尝试查找配置文件的真实路径
    if not os.path.exists(config_path):
        # 尝试在 h 目录下找
        if os.path.exists(os.path.join("h", config_path)):
            config_path = os.path.join("h", config_path)
        # 如果都不存在，将使用原始路径，load_all_config 会尝试生成它
    
    config_data = load_all_config(config_path)
    
    if not config_data:
        print("❌ 无法加载或生成配置文件，程序退出。")
        return
    
    # 交互式检查关键配置
    vrc_config = config_data.get("vrchat", {})
    if not vrc_config.get("username") or not vrc_config.get("password"):
        print("\n⚠️ 检测到 VRChat 配置缺失，请输入账号信息 (直接回车可跳过):")
        try:
            username = input("VRChat 用户名/邮箱: ").strip()
            if username:
                password = input("VRChat 密码: ").strip()
                if password:
                    vrc_config["username"] = username
                    vrc_config["password"] = password
                    
                    # 询问是否保存
                    save = input("是否保存到配置文件? (y/n) [y]: ").strip().lower()
                    if save in ('', 'y', 'yes'):
                        try:
                            # 重新读取原文件以保留注释（如果可能），但这里我们使用的是简单的 json dump，会覆盖注释
                            # 考虑到 ConfigLoader 已经去除了注释，这里只能全量覆盖
                            with open(config_path, 'w', encoding='utf-8') as f:
                                json.dump(config_data, f, indent=4, ensure_ascii=False)
                            print(f"✅ 配置已更新并保存到 {config_path}")
                        except Exception as e:
                            print(f"❌ 保存配置失败: {e}")
        except KeyboardInterrupt:
            print("\n取消输入")
            return

    # 2. 初始化日志
    log_level = config_data.get("bot", {}).get("log_level", "INFO")
    setup_logger(log_level)
    logger = logging.getLogger("Main")

    # 3. 初始化并启动机器人管理器
    bot_manager = BotManager(config_data)
    
    try:
        await bot_manager.start()
    except KeyboardInterrupt:
        logger.info("正在接收停止信号...")
    finally:
        await bot_manager.stop()

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
