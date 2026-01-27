import json
import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("Config")

class ConfigLoader:
    """配置加载器"""
    
    DEFAULT_CONFIG = {
        "bot": {
            "log_level": "INFO",  # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
            "log_retention_days": 30,  # 日志文件保留天数，超过此时间将被自动清理
            "log_archive_policy": {
                "on_error": "archive",  # 出错时的日志归档策略: archive(归档), delete(删除), keep(保留)
                "on_success": "archive"  # 成功时的日志归档策略: archive(归档), delete(删除), keep(保留)
            },
            "admin_qq": [],  # 全局超级管理员QQ号列表，这些用户拥有所有管理员权限
            "group_admins": {},  # 群级管理员配置 {群号: [管理员QQ列表]}，格式如 {"123456": [111111, 222222]}
            "enable_welcome": True,  # 是否启用入群欢迎功能
            "templates": {
                "welcome": "欢迎加入！请查看群公告。",  # 入群欢迎消息模板
                "verify_success": "验证成功！",  # 验证成功消息模板
                "reject_no_user": "无法识别 VRChat 账号，请在验证消息中填写 VRChat 链接或 ID",  # 未找到VRChat用户时的拒绝消息
                "reject_already_bound": "该 VRChat 账号已被 QQ {existing_qq} 绑定",  # 账号已被绑定时拒绝消息
                "reject_no_group": "您未加入指定的 VRChat 群组，请先加群",  # 未加入指定群组时的拒绝消息
                "reject_troll": "系统检测到您的账号存在风险，拒绝入群",  # 检测到风险账号时的拒绝消息
                "verification_request": "[CQ:at,qq={user_id}] 欢迎加入！\n检测到您申请绑定的 VRChat 账号为: {vrc_name}\n为了验证身份，请将您的 VRChat 状态描述(Status Description)修改为以下数字：\n{code}\n修改完成后，请在群内发送 !verify 完成验证。",  # 验证请求消息模板
                "reminder_not_bound": "欢迎！请绑定 VRChat 账号。"  # 未绑定提醒消息模板
            },
            "commands": {
                "query": { "enabled": True, "admin_only": True, "max_results": 50 },  # 查询绑定信息命令
                "bind": { "enabled": True, "admin_only": True },  # 手动绑定命令
                "unbind": { "enabled": True, "admin_only": True },  # 解绑命令
                "unbound": { "enabled": True, "admin_only": True },  # 查询未绑定成员命令
                "list": { "enabled": True, "admin_only": True },  # 查询绑定列表命令
                "search": { "enabled": True, "admin_only": True },  # 搜索VRChat用户命令
                "instances": { "enabled": True, "admin_only": False, "cooldown": 60 },  # 查询活跃实例命令，冷却时间60秒
                "me": { "enabled": True, "admin_only": False },  # 查看我的绑定信息命令
                "code": { "enabled": True, "admin_only": False }  # 重新获取验证码命令
            },
            "features": {
                "auto_approve_group_request": False,  # 是否自动审批入群申请
                "auto_bind_on_join": True  # 是否在入群时自动触发绑定流程
            },
            "verification": {
                "mode": "mixed",  # 验证模式: mixed(混合), strict(严格), disabled(禁用)
                "group_id": "",  # 目标VRChat群组ID，用于群组验证
                "timeout": 300,  # 验证超时时间(秒)
                "code_expiry": 300,  # 验证码过期时间(秒)
                "auto_rename": True,  # 验证成功后是否自动修改群昵称
                "check_occupy": True,  # 是否检查VRChat账号是否已被占用
                "check_group_membership": False,  # 是否检查VRChat群组成员资格
                "check_troll": False,  # 是否启用风险账号检测
                "auto_assign_role": False,  # 验证成功后是否自动分配角色
                "target_role_id": ""  # 目标角色ID，用于自动分配角色
            }
        },
        "database": {
            "type": "mysql",  # 数据库类型: sqlite(推荐) 或 mysql
            "path": "data/bot.db",  # SQLite数据库文件路径
            "host": "localhost",  # MySQL主机地址(使用MySQL时生效)
            "port": 3306,  # MySQL端口(使用MySQL时生效)
            "user": "root",  # MySQL用户名(使用MySQL时生效)
            "password": "",  # MySQL密码(使用MySQL时生效)
            "database": "vrc_qq_bot"  # MySQL数据库名(使用MySQL时生效)
        },
        "napcat": {
            "ws_url": "ws://127.0.0.1:3001",  # NapCat WebSocket连接地址
            "token": "",  # NapCat API令牌，留空表示不需要认证
            "ws_max_retries": 10,  # WebSocket最大重连次数
            "ws_initial_delay": 5.0,  # WebSocket初始重连延迟(秒)
            "ws_max_delay": 60.0  # WebSocket最大重连延迟(秒)
        },
        "vrchat": {
            "username": "",  # VRChat用户名
            "password": "",  # VRChat密码
            "totp_secret": "",  # VRChat两步验证密钥(可选)
            "user_agent": "VRCQQBot/2.0",  # VRChat API用户代理
            "proxy": ""  # 代理服务器地址，格式如: http://127.0.0.1:8080
        }
    }

    @staticmethod
    def load_config(config_path: str) -> Optional[Dict[str, Any]]:

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
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    def get(self, key: str, default: Any = None) -> Any:

        return self.data.get(key, default)
    
    @property
    def bot(self) -> Dict[str, Any]:
        """获取机器人配置"""
        return self.data.get("bot", {})
    
    @property
    def database(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.data.get("database", {})
    
    @property
    def group_admins(self) -> Dict[str, List[int]]:
        """获取群管理员配置
        
        Returns:
            群管理员配置字典，格式为 {群号: [管理员QQ列表]}
        """
        return self.data.get("bot", {}).get("group_admins", {})

    def __getattr__(self, name: str) -> Any:

        # 1. 尝试从 bot 配置中获取
        bot_config = self.data.get("bot", {})
        if name in bot_config:
            return bot_config[name]
            
        # 2. 尝试从根配置中获取
        if name in self.data:
            return self.data[name]
            
        raise AttributeError(f"'GlobalConfig' object has no attribute '{name}'")
