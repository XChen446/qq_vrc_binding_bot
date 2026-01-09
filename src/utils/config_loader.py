"""
配置加载器
处理配置文件的加载、验证和动态更新
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from utils.message_template import DEFAULT_TEMPLATES


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_file: str):
        """
        初始化配置加载器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = None
        self.watch_task = None
        
    def load(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 验证配置
            self._validate_config()
            
            # 从环境变量覆盖
            self._override_from_env()
            
            logger.info(f"配置文件加载成功: {self.config_file}")
            return self.config
            
        except Exception as e:
            logger.exception(f"加载配置文件失败: {e}")
            raise
    
    def _validate_config(self):
        """验证配置"""
        try:
            # 验证应用配置
            app_config = self.config.get('app', {})
            if 'log_level' not in app_config:
                app_config['log_level'] = 'INFO'
            
            # 验证VRChat配置
            vrc_config = self.config.get('vrchat', {})
            required_vrc_fields = ['username', 'password']
            for field in required_vrc_fields:
                if field not in vrc_config:
                    logger.warning(f"VRChat配置缺少必要字段: {field}")
            
            # 验证Napcat配置
            napcat_config = self.config.get('napcat', {})
            if 'host' not in napcat_config:
                napcat_config['host'] = '127.0.0.1'
            if 'port' not in napcat_config:
                napcat_config['port'] = 3000
            
            # 验证群组配置
            groups_config = self.config.get('groups', {})
            managed_groups = groups_config.get('managed_groups', [])
            
            for group in managed_groups:
                if 'group_id' not in group:
                    raise ValueError("群组配置缺少group_id字段")
                if 'vrc_group_id' not in group:
                    logger.warning(f"群组 {group.get('group_id')} 缺少vrc_group_id字段")
            
            logger.info("配置验证完成")
            
        except Exception as e:
            logger.exception(f"配置验证失败: {e}")
            raise
    
    def _override_from_env(self):
        """从环境变量覆盖配置"""
        try:
            # VRChat配置
            vrc_config = self.config.get('vrchat', {})
            
            if os.getenv('VRCHAT_USERNAME'):
                vrc_config['username'] = os.getenv('VRCHAT_USERNAME')
            if os.getenv('VRCHAT_PASSWORD'):
                vrc_config['password'] = os.getenv('VRCHAT_PASSWORD')
            if os.getenv('TOTP_SECRET'):
                if 'two_factor' not in vrc_config:
                    vrc_config['two_factor'] = {}
                vrc_config['two_factor']['totp_secret'] = os.getenv('TOTP_SECRET')
            
            # 代理配置
            if os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'):
                if 'proxy' not in vrc_config:
                    vrc_config['proxy'] = {}
                
                if os.getenv('HTTP_PROXY'):
                    vrc_config['proxy']['http_proxy'] = os.getenv('HTTP_PROXY')
                if os.getenv('HTTPS_PROXY'):
                    vrc_config['proxy']['https_proxy'] = os.getenv('HTTPS_PROXY')
                
                vrc_config['proxy']['enabled'] = True
            
            # Napcat配置
            napcat_config = self.config.get('napcat', {})
            if os.getenv('NAPCAT_ACCESS_TOKEN'):
                napcat_config['access_token'] = os.getenv('NAPCAT_ACCESS_TOKEN')
            if os.getenv('NAPCAT_WEBHOOK_URL'):
                napcat_config['webhook_url'] = os.getenv('NAPCAT_WEBHOOK_URL')
            
        except Exception as e:
            logger.warning(f"从环境变量覆盖配置时出错: {e}")
    
    def save(self, config: Optional[Dict[str, Any]] = None):
        """
        保存配置到文件
        
        Args:
            config: 配置字典（默认使用当前配置）
        """
        try:
            if config:
                self.config = config
            
            if not self.config:
                raise ValueError("没有可保存的配置")
            
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 备份原文件
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.yaml.bak')
                backup_file.write_text(self.config_file.read_text(), encoding='utf-8')
            
            # 保存新配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置保存成功: {self.config_file}")
            
        except Exception as e:
            logger.exception(f"保存配置失败: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点号分隔）
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            if not self.config:
                return default
            
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.debug(f"获取配置值失败: {key} - {e}")
            return default
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键（支持点号分隔）
            value: 配置值
        """
        try:
            if not self.config:
                self.config = {}
            
            keys = key.split('.')
            config = self.config
            
            # 遍历到倒数第二层
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置最终值
            config[keys[-1]] = value
            
            logger.debug(f"配置值已设置: {key} = {value}")
            
        except Exception as e:
            logger.exception(f"设置配置值失败: {key} - {e}")
            raise
    
    def reload(self):
        """重新加载配置"""
        try:
            logger.info("重新加载配置...")
            self.load()
            logger.info("配置重新加载完成")
            
        except Exception as e:
            logger.exception(f"重新加载配置失败: {e}")
            raise
    
    def export_template(self) -> str:
        """
        导出配置模板
        
        Returns:
            模板内容
        """
        template = {
            'app': {
                'name': 'QQ-VRC双向绑定机器人',
                'version': '1.0.0',
                'enabled': True,
                'log_level': 'INFO',
                'data_dir': './data',
                'log_dir': './logs'
            },
            'napcat': {
                'enabled': True,
                'host': '127.0.0.1',
                'port': 3000,
                'access_token': '',
                'webhook_url': ''
            },
            'vrchat': {
                'username': '',
                'password': '',
                'api_key': 'JlE5Jldo5JibnkqO',
                'proxy': {
                    'enabled': False,
                    'http_proxy': 'http://127.0.0.1:7890',
                    'https_proxy': 'http://127.0.0.1:7890'
                },
                'two_factor': {
                    'enabled': False,
                    'method': 'totp',
                    'totp_secret': ''
                }
            },
            'groups': {
                'managed_groups': [
                    {
                        'group_id': 123456789,
                        'enabled': True,
                        'vrc_group_id': 'grp_fdd4cdf6-b3e0-4be3-a040-5b8abf2617f4',
                        'auto_assign_role': 'rol_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                        'join_request_keyword': 'VRChat用户ID',
                        'admin_qq_ids': [111111, 222222]
                    }
                ]
            },
            'messages': DEFAULT_TEMPLATES,
            'review': {
                'auto_approve': True,
                'userid_pattern': 'usr_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                'check_user_status': True,
                'on_role_fail': 'notify_admin'
            },
            'database': {
                'type': 'json',
                'file_path': './data/user_bindings.json',
                'backup_enabled': True,
                'backup_interval': 86400
            }
        }
        
        return yaml.dump(template, default_flow_style=False, allow_unicode=True)
    
    def get_config_info(self) -> Dict[str, Any]:
        """
        获取配置信息
        
        Returns:
            配置信息字典
        """
        return {
            'config_file': str(self.config_file),
            'config_loaded': self.config is not None,
            'sections': list(self.config.keys()) if self.config else [],
            'file_exists': self.config_file.exists(),
            'file_size': self.config_file.stat().st_size if self.config_file.exists() else 0
        }