import logging
from typing import Dict, Any

logger = logging.getLogger("VRCConfig")

class VRCConfig:
    def __init__(self, data: Dict[str, Any]):
        vrc_data = data.get("vrchat", {})
        self.username: str = vrc_data.get("username", "")
        self.password: str = vrc_data.get("password", "")
        self.totp_secret: str = vrc_data.get("totp_secret", "")
        self.user_agent: str = vrc_data.get("user_agent", "")
        self.proxy: str = vrc_data.get("proxy", "")
        
        # 验证相关的配置
        bot_data = data.get("bot", {})
        self.verification: Dict[str, Any] = bot_data.get("verification", {})
        
        logger.debug(f"已加载 VRChat 配置: username={self.username}")

    @property
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return bool(self.username and self.password)
    
    @property
    def has_2fa(self) -> bool:
        """是否配置了 2FA"""
        return bool(self.totp_secret)
