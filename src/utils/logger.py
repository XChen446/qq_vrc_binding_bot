"""
日志系统
支持多级别日志记录和文件输出
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
import json


class AppLogger:
    """应用日志管理器"""
    
    # 日志级别映射
    LOG_LEVELS = {
        'DEBUG': 'DEBUG',
        'INFO': 'INFO',
        'WARNING': 'WARNING',
        'ERROR': 'ERROR',
        'CRITICAL': 'CRITICAL'
    }
    
    def __init__(self, log_dir: str = "./logs", 
                 log_level: str = "INFO",
                 max_file_size: str = "10 MB",
                 retention_days: int = 30):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录
            log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
            max_file_size: 单个日志文件最大大小
            retention_days: 日志保留天数
        """
        self.log_dir = Path(log_dir)
        self.log_level = log_level
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志
        self._configure_logger()
        
    def _configure_logger(self):
        """配置日志系统"""
        # 移除默认的日志处理器
        logger.remove()
        
        # 控制台输出
        logger.add(
            sys.stderr,
            level=self.log_level,
            format=self._get_console_format(),
            colorize=True,
            backtrace=True,
            diagnose=True
        )
        
        # 主日志文件（所有级别）
        main_log_file = self.log_dir / "app.log"
        logger.add(
            str(main_log_file),
            level=self.log_level,
            format=self._get_file_format(),
            rotation=self.max_file_size,
            retention=f"{self.retention_days} days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        
        # 错误日志文件（仅ERROR及以上）
        error_log_file = self.log_dir / "error.log"
        logger.add(
            str(error_log_file),
            level="ERROR",
            format=self._get_file_format(),
            rotation=self.max_file_size,
            retention=f"{self.retention_days} days",
            compression="zip",
            enqueue=True,
            backtrace=True,
            diagnose=True
        )
        
        # HTTP请求日志（详细日志）
        http_log_file = self.log_dir / "http.log"
        logger.add(
            str(http_log_file),
            level="DEBUG",
            format=self._get_file_format(),
            filter=lambda record: "http" in record["extra"],
            rotation=self.max_file_size,
            retention=f"{self.retention_days} days",
            compression="zip",
            enqueue=True
        )
        
        # VRChat API日志
        api_log_file = self.log_dir / "vrchat_api.log"
        logger.add(
            str(api_log_file),
            level="DEBUG",
            format=self._get_file_format(),
            filter=lambda record: "vrchat_api" in record["extra"],
            rotation=self.max_file_size,
            retention=f"{self.retention_days} days",
            compression="zip",
            enqueue=True
        )
        
        # QQ Bot日志
        qq_log_file = self.log_dir / "qq_bot.log"
        logger.add(
            str(qq_log_file),
            level="DEBUG",
            format=self._get_file_format(),
            filter=lambda record: "qq_bot" in record["extra"],
            rotation=self.max_file_size,
            retention=f"{self.retention_days} days",
            compression="zip",
            enqueue=True
        )
        
    def _get_console_format(self) -> str:
        """获取控制台日志格式"""
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    
    def _get_file_format(self) -> str:
        """获取文件日志格式"""
        return (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    
    def get_logger(self, name: str = None) -> logger:
        """
        获取日志器
        
        Args:
            name: 日志器名称
            
        Returns:
            日志器实例
        """
        if name:
            return logger.bind(name=name)
        return logger
    
    def log_http_request(self, method: str, url: str, 
                        headers: Optional[Dict] = None,
                        data: Optional[Any] = None,
                        response: Optional[Any] = None):
        """
        记录HTTP请求
        
        Args:
            method: 请求方法
            url: 请求URL
            headers: 请求头
            data: 请求数据
            response: 响应对象
        """
        try:
            log_data = {
                'method': method,
                'url': url,
                'headers': headers,
                'data': data
            }
            
            if response is not None:
                log_data['response_status'] = getattr(response, 'status_code', None) or getattr(response, 'status', None)
                log_data['response_headers'] = dict(response.headers) if hasattr(response, 'headers') else None
                
                # 尝试获取响应内容
                try:
                    if hasattr(response, 'text'):
                        log_data['response_body'] = response.text[:1000]  # 限制长度
                    elif hasattr(response, 'content'):
                        log_data['response_body'] = response.content[:1000]
                except:
                    log_data['response_body'] = '[无法获取响应内容]'
            
            # 使用专门的HTTP日志器
            http_logger = self.get_logger('http')
            http_logger.debug(f"HTTP请求: {json.dumps(log_data, ensure_ascii=False, indent=2)}")
            
        except Exception as e:
            logger.error(f"记录HTTP请求失败: {e}")
    
    def log_vrchat_api(self, action: str, user_id: str = None, 
                      group_id: str = None, role_id: str = None,
                      result: str = None, error: str = None):
        """
        记录VRChat API调用
        
        Args:
            action: 操作类型
            user_id: 用户ID
            group_id: 群组ID
            role_id: 角色ID
            result: 结果
            error: 错误信息
        """
        try:
            log_data = {
                'action': action,
                'user_id': user_id,
                'group_id': group_id,
                'role_id': role_id,
                'result': result,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            
            # 使用专门的VRChat API日志器
            api_logger = self.get_logger('vrchat_api')
            
            if error:
                api_logger.error(f"VRChat API错误: {json.dumps(log_data, ensure_ascii=False)}")
            elif result == 'success':
                api_logger.info(f"VRChat API成功: {json.dumps(log_data, ensure_ascii=False)}")
            else:
                api_logger.debug(f"VRChat API调用: {json.dumps(log_data, ensure_ascii=False)}")
                
        except Exception as e:
            logger.error(f"记录VRChat API调用失败: {e}")
    
    def log_qq_event(self, event_type: str, user_id: int = None,
                    group_id: int = None, message: str = None,
                    result: str = None, error: str = None):
        """
        记录QQ Bot事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            group_id: 群组ID
            message: 消息内容
            result: 结果
            error: 错误信息
        """
        try:
            log_data = {
                'event_type': event_type,
                'user_id': user_id,
                'group_id': group_id,
                'message': message[:200] if message else None,  # 限制长度
                'result': result,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            
            # 使用专门的QQ Bot日志器
            qq_logger = self.get_logger('qq_bot')
            
            if error:
                qq_logger.error(f"QQ Bot错误: {json.dumps(log_data, ensure_ascii=False)}")
            elif result == 'success':
                qq_logger.info(f"QQ Bot成功: {json.dumps(log_data, ensure_ascii=False)}")
            else:
                qq_logger.debug(f"QQ Bot事件: {json.dumps(log_data, ensure_ascii=False)}")
                
        except Exception as e:
            logger.error(f"记录QQ Bot事件失败: {e}")
    
    def log_operation(self, operation: str, operator: str = None,
                     target: str = None, details: Dict = None,
                     result: str = 'success', error: str = None):
        """
        记录操作日志
        
        Args:
            operation: 操作名称
            operator: 操作者
            target: 目标
            details: 详细信息
            result: 结果
            error: 错误信息
        """
        try:
            log_message = f"操作: {operation}"
            
            if operator:
                log_message += f" | 操作者: {operator}"
            if target:
                log_message += f" | 目标: {target}"
            if details:
                log_message += f" | 详情: {json.dumps(details, ensure_ascii=False)}"
            if result:
                log_message += f" | 结果: {result}"
            if error:
                log_message += f" | 错误: {error}"
            
            if result == 'success':
                logger.info(log_message)
            elif result == 'warning':
                logger.warning(log_message)
            else:
                logger.error(log_message)
                
        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
    
    def set_log_level(self, level: str):
        """
        设置日志级别
        
        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        """
        if level in self.LOG_LEVELS:
            self.log_level = level
            # 重新配置日志器
            self._configure_logger()
            logger.info(f"日志级别已设置为: {level}")
        else:
            logger.warning(f"无效的日志级别: {level}")
    
    def cleanup_old_logs(self, days: int = 30):
        """
        清理旧日志文件
        
        Args:
            days: 保留天数
        """
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            
            for log_file in self.log_dir.glob('*.log'):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    logger.info(f"删除旧日志: {log_file}")
            
            # 清理压缩的日志
            for zip_file in self.log_dir.glob('*.zip'):
                if zip_file.stat().st_mtime < cutoff_time:
                    zip_file.unlink()
                    logger.info(f"删除旧压缩日志: {zip_file}")
                    
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
    
    def get_log_files(self) -> Dict[str, str]:
        """
        获取日志文件列表
        
        Returns:
            日志文件字典 {名称: 路径}
        """
        log_files = {}
        
        for log_file in self.log_dir.glob('*.log'):
            log_files[log_file.stem] = str(log_file)
        
        return log_files
    
    def export_logs(self, start_date: str = None, end_date: str = None) -> str:
        """
        导出日志
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            导出的文件路径
        """
        try:
            from datetime import datetime, timedelta
            
            export_file = self.log_dir / f"exported_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write(f"日志导出\n")
                f.write(f"时间范围: {start_date} 至 {end_date}\n")
                f.write(f"导出时间: {datetime.now()}\n")
                f.write("=" * 50 + "\n\n")
                
                # 这里可以添加实际的日志内容导出逻辑
                # 暂时只创建空文件
                f.write("[日志内容导出功能待实现]\n")
            
            logger.info(f"日志导出完成: {export_file}")
            return str(export_file)
            
        except Exception as e:
            logger.error(f"导出日志失败: {e}")
            return ""