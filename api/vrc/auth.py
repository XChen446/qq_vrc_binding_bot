import aiohttp
import logging
import pyotp
from urllib.parse import urljoin
from typing import Optional, Dict, Any

logger = logging.getLogger("VRChatAPI.Auth")

class VRCAuth:
    def __init__(self, client):
        self.client = client
        self.base_url = client.BASE_URL

    async def login(self, username=None, password=None, totp_secret=None) -> bool:
        """异步登录流程"""
        username = username or self.client.config.username
        password = password or self.client.config.password
        
        if not username or not password:
            logger.error("未找到用户名或密码")
            return False

        auth = aiohttp.BasicAuth(username, password)
        try:
            session = await self.client.get_session()
            url = urljoin(self.base_url, "auth/user")
            async with session.get(url, auth=auth) as response:
                data = await response.json()
                
                if "requiresTwoFactorAuth" in data:
                    return await self._handle_2fa(data, totp_secret)
                
                if response.status == 200:
                    logger.info("VRChat 登录成功")
                    self.client.save_cookies()
                    return True
                else:
                    logger.error(f"登录失败 ({response.status}): {data}")
                    return False
        except Exception as e:
            logger.error(f"登录过程发生异常: {e}")
            return False

    async def _handle_2fa(self, data, totp_secret=None) -> bool:
        verification_type = data["requiresTwoFactorAuth"][0]
        code = None
        
        if verification_type == "totp":
            secret = totp_secret or self.client.config.totp_secret
            if secret:
                totp = pyotp.TOTP(secret)
                code = totp.now()
            else:
                # 阻塞式输入作为兜底
                code = input("请输入身份验证器 6 位验证码: ")
        elif verification_type == "emailOtp":
            code = input("请输入邮箱验证码: ")
            
        if code:
            return await self._verify_2fa(code, verification_type)
        return False

    async def _verify_2fa(self, code, method="totp") -> bool:
        endpoint = f"auth/twofactorauth/{method}/verify"
        url = urljoin(self.base_url, endpoint)
        try:
            session = await self.client.get_session()
            async with session.post(url, json={"code": code}) as response:
                if response.status == 200:
                    logger.info("2FA 验证通过")
                    self.client.save_cookies()
                    return True
                return False
        except Exception as e:
            logger.error(f"2FA 校验异常: {e}")
            return False

    async def verify_auth(self) -> bool:
        """异步验证会话有效性"""
        try:
            data = await self.client._request("GET", "auth/user", retry_on_auth=False)
            if data and "id" in data:
                logger.info(f"当前在线用户: {data['displayName']}")
                return True
        except:
            pass
        return False
