import logging
import os
import sys
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True, wrap=True)

class ColoredFormatter(logging.Formatter):
    """自定义日志格式化器，为不同级别添加颜色"""
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        import copy
        record_cp = copy.copy(record)
        
        color = self.COLORS.get(record_cp.levelno, "")
        if color:
            record_cp.levelname = f"{color}{record_cp.levelname}{Style.RESET_ALL}"
            if record_cp.levelno >= logging.WARNING:
                record_cp.msg = f"{color}{record_cp.msg}{Style.RESET_ALL}"
        
        return super().format(record_cp)

def setup_logger(log_level_str="INFO"):
    """全局日志初始化"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    log_level = level_map.get(log_level_str.upper(), logging.INFO)
    
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    console_handler.setLevel(log_level)

    # 主日志文件
    app_handler = logging.FileHandler(os.path.join(log_dir, "app.log"), mode='a', encoding='utf-8')
    app_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    app_handler.setLevel(logging.DEBUG)

    # QQ API 日志
    qq_handler = logging.FileHandler(os.path.join(log_dir, "qq_api.log"), mode='a', encoding='utf-8')
    qq_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    qq_handler.setLevel(logging.DEBUG)

    # VRC API 日志
    vrc_handler = logging.FileHandler(os.path.join(log_dir, "vrc_api.log"), mode='a', encoding='utf-8')
    vrc_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    vrc_handler.setLevel(logging.DEBUG)

    # 访问日志
    access_handler = logging.FileHandler(os.path.join(log_dir, "access.log"), mode='a', encoding='utf-8')
    access_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    access_handler.setLevel(logging.INFO)

    # 基础配置
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[console_handler, app_handler],
        force=True
    )
    
    # 专用 Logger 配置
    logging.getLogger("QQBot").addHandler(qq_handler)
    logging.getLogger("VRChatAPI").addHandler(vrc_handler)
    logging.getLogger("Access").addHandler(access_handler)

    # 屏蔽第三方库 Debug 日志
    logging.getLogger("websockets").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.INFO)
    
    logging.info(f"日志系统初始化完成，等级: {log_level_str}")
