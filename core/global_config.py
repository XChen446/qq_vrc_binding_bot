import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("Config")

class ConfigLoader:
    """配置加载器"""
    
    DEFAULT_CONFIG = {
        "bot": {
            "log_level": "INFO",
            "log_retention_days": 30,
            "log_archive_policy": {
                "on_error": "archive",
                "on_success": "archive"
            },
            "admin_qq": [],
            "group_whitelist": [],
            "enable_welcome": True,
            "templates": {
                "welcome": "欢迎加入！请查看群公告。",
                "verify_success": "验证成功！",
                "reject_no_user": "无法识别 VRChat 账号，请在验证消息中填写 VRChat 链接或 ID",
                "reject_already_bound": "该 VRChat 账号已被 QQ {existing_qq} 绑定",
                "reject_no_group": "您未加入指定的 VRChat 群组，请先加群",
                "reject_troll": "系统检测到您的账号存在风险，拒绝入群",
                "verification_request": "[CQ:at,qq={user_id}] 欢迎加入！\n检测到您申请绑定的 VRChat 账号为: {vrc_name}\n为了验证身份，请将您的 VRChat 状态描述(Status Description)修改为以下数字：\n{code}\n修改完成后，请在群内发送 !verify 完成验证。",
                "reminder_not_bound": "欢迎！请绑定 VRChat 账号。"
            },
            "commands": {
                "query": { "enabled": True, "admin_only": True, "max_results": 50 },
                "bind": { "enabled": True, "admin_only": True },
                "unbind": { "enabled": True, "admin_only": True },
                "unbound": { "enabled": True, "admin_only": True },
                "list": { "enabled": True, "admin_only": True },
                "search": { "enabled": True, "admin_only": True },
                "instances": { "enabled": True, "admin_only": False, "cooldown": 60 },
                "me": { "enabled": True, "admin_only": False },
                "code": { "enabled": True, "admin_only": False }
            },
            "features": {
                "auto_approve_group_request": False,
                "auto_bind_on_join": True
            },
            "verification": {
                "mode": "mixed",
                "group_id": "",
                "timeout": 300,
                "code_expiry": 300,
                "auto_rename": True,
                "check_occupy": True,
                "check_group_membership": False,
                "check_troll": False,
                "auto_assign_role": False,
                "target_role_id": ""
            }
        },
        "database": {
            "type": "sqlite",
            "path": "data/bot.db",
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "vrc_qq_bot"
        },
        "napcat": {
            "ws_url": "ws://127.0.0.1:3001",
            "token": "",
            "ws_max_retries": 10,
            "ws_initial_delay": 5.0,
            "ws_max_delay": 60.0
        },
        "vrchat": {
            "username": "",
            "password": "",
            "totp_secret": "",
            "user_agent": "VRCQQBot/2.0",
            "proxy": ""
        }
    }

    @staticmethod
    def load_config(config_path: str) -> Optional[Dict[str, Any]]:
        """加载配置，不存在则创建默认"""
        if not os.path.exists(config_path):
            return ConfigLoader._create_default_config(config_path)
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 检查并合并新字段
            if ConfigLoader._deep_merge(ConfigLoader.DEFAULT_CONFIG, config):
                logger.info(f"检测到配置文件缺失新字段，正在更新 {config_path}...")
                ConfigLoader._save_json(config_path, config)
                
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return None

    @staticmethod
    def _create_default_config(config_path: str) -> None:
        logger.warning(f"配置文件 {config_path} 不存在，尝试创建默认配置...")
        try:
            ConfigLoader._save_json(config_path, ConfigLoader.DEFAULT_CONFIG)
            logger.info(f"默认配置已创建: {config_path}")
            logger.warning("请编辑配置文件，填写必要的配置项后重新运行")
            return None
        except Exception as e:
            logger.error(f"创建默认配置失败: {e}")
            return None

    @staticmethod
    def _save_json(file_path: str, data: Dict[str, Any]):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def _deep_merge(default: Dict, current: Dict) -> bool:
        """递归合并配置"""
        updated = False
        for key, value in default.items():
            if key not in current:
                current[key] = value
                updated = True
            elif isinstance(value, dict) and isinstance(current[key], dict):
                if ConfigLoader._deep_merge(value, current[key]):
                    updated = True
        return updated

def load_all_config(config_path: str) -> Optional[Dict[str, Any]]:
    """兼容旧代码的入口"""
    return ConfigLoader.load_config(config_path)


class GlobalConfig:
    """全局配置类，封装配置数据访问"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)
    
    @property
    def bot(self) -> Dict[str, Any]:
        return self.data.get("bot", {})
    
    @property
    def database(self) -> Dict[str, Any]:
        return self.data.get("database", {})

    def __getattr__(self, name: str) -> Any:
        # 1. 尝试从 bot 配置中获取
        bot_config = self.data.get("bot", {})
        if name in bot_config:
            return bot_config[name]
            
        # 2. 尝试从根配置中获取
        if name in self.data:
            return self.data[name]
            
        raise AttributeError(f"'GlobalConfig' object has no attribute '{name}'")
