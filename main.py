import argparse
import os
import sys
import asyncio
import logging
import json
# 确保能找到项目模块 (将当前目录加入 sys.path)
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from src.utils.logger import setup_logger
from src.core.global_config import load_all_config
from src.core.bot_manager import BotManager

async def async_main():
    """
    系统的初始化
    """
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="VRChat QQ 绑定机器人 (重构版)")
    parser.add_argument("--config", default="config/config.json", help="配置文件路径")
    args = parser.parse_args()

    # 2. 加载配置
    config_path = args.config
    
    config_data = load_all_config(config_path)
    
    if not config_data:
        print("❌ 无法加载或生成配置文件，程序退出。")
        return
    
    # 交互式检查关键配置 (如果配置为空，提示用户输入)
    vrc_config = config_data.get("vrchat", {})
    if not vrc_config.get("username") or not vrc_config.get("password"):
        print("\n检测到 VRChat 配置缺失，请输入账号信息 (直接回车可跳过):")
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

                            with open(config_path, 'w', encoding='utf-8') as f:
                                json.dump(config_data, f, indent=4, ensure_ascii=False)
                            print(f"✅ 配置已更新并保存到 {config_path}")
                        except Exception as e:
                            print(f"❌ 保存配置失败: {e}")
        except KeyboardInterrupt:
            print("\n取消输入")
            return

    # 3. 初始化日志系统
    bot_config = config_data.get("bot", {})
    log_level = bot_config.get("log_level", "INFO")
    retention_days = bot_config.get("log_retention_days", 30)
    archive_policy = bot_config.get("log_archive_policy", None)
    
    setup_logger(log_level, retention_days=retention_days, archive_policy=archive_policy)
    logger = logging.getLogger("Main")

    # 4. 初始化并启动机器人管理器
    bot_manager = BotManager(config_data, config_path)
    
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