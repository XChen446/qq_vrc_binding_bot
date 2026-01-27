import logging
import os
import sys
import gzip
from logging.handlers import TimedRotatingFileHandler
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

class LogColors:
    """定义日志颜色"""
    DEBUG = Fore.CYAN
    INFO = Fore.GREEN
    WARNING = Fore.YELLOW
    ERROR = Fore.RED
    CRITICAL = Fore.RED + Style.BRIGHT
    RESET = Style.RESET_ALL

class ColoredFormatter(logging.Formatter):
    """
    自定义日志格式化器，带颜色支持
    格式: Time - Name - Level - Message
    """
    def format(self, record):
        # 保存原始属性
        original_levelname = record.levelname
        original_msg = record.msg

        # 获取颜色
        color = getattr(LogColors, record.levelname, LogColors.INFO)
        
        # 格式化 LevelName
        if record.levelno >= logging.WARNING:
            # 警告及以上，整行或关键部分标色
            record.levelname = f"{color}{record.levelname}{LogColors.RESET}"
            record.msg = f"{color}{record.msg}{LogColors.RESET}"
        else:
            record.levelname = f"{color}{record.levelname}{LogColors.RESET}"

        # 格式化输出
        formatted = super().format(record)

        # 还原属性 (防止污染其他 Handler)
        record.levelname = original_levelname
        record.msg = original_msg
        
        return formatted

def check_file_has_error(file_path: str) -> bool:
    """检查文件是否包含 ERROR 或 CRITICAL 日志"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if "ERROR" in line or "CRITICAL" in line:
                    return True
    except Exception:
        pass
    return False

def archive_old_logs(log_dir: str, policy: dict = None):
    """
    启动时归档旧的日志文件
    :param log_dir: 日志目录
    :param policy: 归档策略 { "on_error": "archive"|"delete"|"keep", "on_success": ... }
    """
    if not os.path.exists(log_dir):
        return

    if policy is None:
        policy = {"on_error": "archive", "on_success": "archive"}

    # 1. 准备归档目录
    archive_dir = os.path.join(log_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    # 2. 查找文件并决定动作
    files_to_archive = []
    files_to_delete = []
    
    # 获取所有日志文件
    log_files = []
    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)
        if not os.path.isfile(file_path):
            continue
        if filename.endswith(".log") or ".log." in filename:
            log_files.append(filename)

    if not log_files:
        return

    print(f"🔍 正在扫描旧日志 ({len(log_files)} 个文件)...")

    for filename in log_files:
        file_path = os.path.join(log_dir, filename)
        has_error = check_file_has_error(file_path)
        
        action = policy.get("on_error" if has_error else "on_success", "archive")
        
        if action == "archive":
            files_to_archive.append(filename)
        elif action == "delete":
            files_to_delete.append(filename)
        # elif action == "keep": do nothing

    # 3. 执行归档
    if files_to_archive:
        archived_count = 0
        for filename in files_to_archive:
            file_path = os.path.join(log_dir, filename)
            gz_filename = f"{filename}.gz"
            gz_path = os.path.join(archive_dir, gz_filename)
            
            try:
                with open(file_path, 'rb') as f_in:
                    with gzip.open(gz_path, 'wb') as f_out:
                        f_out.writelines(f_in)
                
                # 归档后删除原文件
                os.remove(file_path)
                archived_count += 1
                
            except Exception as e:
                print(f"⚠️ 无法归档文件 {filename}: {e}")
        
        if archived_count > 0:
            print(f"📦 已归档 {archived_count} 个日志文件到 {archive_dir}")

    # 4. 执行直接删除
    if files_to_delete:
        print(f"🗑️ 正在清理 {len(files_to_delete)} 个无用日志文件...")
        for filename in files_to_delete:
            try:
                os.remove(os.path.join(log_dir, filename))
            except Exception as e:
                print(f"⚠️ 无法删除文件 {filename}: {e}")

def setup_logger(log_level_str: str = "INFO", log_dir: str = "logs", retention_days: int = 30, archive_policy: dict = None):
    # 0. 启动前归档旧日志
    archive_old_logs(log_dir, archive_policy)

    # 1. 基础配置
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Root 捕获所有，由 Handlers 过滤

    # 清除旧 Handlers
    root_logger.handlers.clear()

    # 2. 定义格式化器
    # 文件日志格式 (无颜色)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # 控制台日志格式 (带颜色)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. 添加控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 4. 定义文件 Handler 辅助函数
    def add_file_handler(logger_obj, filename: str, level: int = logging.DEBUG):
        """为指定的 Logger 添加文件处理器"""
        file_path = os.path.join(log_dir, filename)
        handler = TimedRotatingFileHandler(
            file_path,
            when='midnight',
            interval=1,
            backupCount=retention_days, # 使用配置的保留天数
            encoding='utf-8'
        )
        handler.setLevel(level)
        handler.setFormatter(file_formatter)
        logger_obj.addHandler(handler)

    # 5. 配置各模块日志文件
    
    # app.log - 主日志文件
    # 记录 INFO 及以上级别，作为一般的操作记录
    add_file_handler(root_logger, "app.log", level=log_level)

    # error.log - 错误日志
    # 只记录 ERROR 及以上级别
    add_file_handler(root_logger, "error.log", level=logging.ERROR)

    # vrchat_api.log - VRChat API日志
    # 对应 VRChatAPI Logger
    vrc_logger = logging.getLogger("VRChatAPI")
    add_file_handler(vrc_logger, "vrchat_api.log", level=logging.DEBUG)

    # qq_bot.log - QQ Bot日志
    # 对应 QQBot Logger (包括 QQBot.API 等子模块)
    qq_logger = logging.getLogger("QQBot")
    add_file_handler(qq_logger, "qq_bot.log", level=logging.DEBUG)

    # 6. 调整第三方库日志
    logging.getLogger("websockets").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("PIL").setLevel(logging.INFO)

    logging.info(f"日志系统初始化完成 | Level: {log_level_str} | Dir: {log_dir}")
