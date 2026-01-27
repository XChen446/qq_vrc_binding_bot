# 导出core模块中的常用函数和类
from .global_config import load_all_config, GlobalConfig
from .bot_manager import BotManager

__all__ = [
    'load_all_config',
    'GlobalConfig',
    'BotManager'
]