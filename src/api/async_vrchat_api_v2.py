"""
改进版异步VRChat API客户端
支持Cookie持久化、可选TOTP、更好的错误处理
"""

import asyncio
import base64
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from starlette.datastructures import URL

import aiohttp
from yarl import URL
from loguru import logger
import pyotp


class ImprovedAsyncVRChatAPIClient:
    """改进版异步VRChat API客户端"""
    
    BASE_URL = "https://api.vrchat.cloud/api/1"
    
    def __init__(self, username: str, password: str, 
                 cookie_file: Optional[str] = None,
                 proxy_config: Optional[Dict] = None,
                 totp_secret: Optional[str] = None,
                 auto_generate_totp: bool = False,
                 api_key: str = "JlE5Jldo5JibnkqO"):
        """
        初始化改进版VRChat API客户端
        
        Args:
            username: VRChat用户名
            password: VRChat密码
            cookie_file: Cookie存储文件路径
            proxy_config: 代理配置
            totp_secret: TOTP密钥（可选）
            auto_generate_totp: 是否自动生成TOTP验证码
            api_key: VRChat API密钥
        """
        self.username = username
        self.password = password
        self.api_key = api_key
        self.proxy_config = proxy_config or {}
        self.totp_secret = totp_secret
        self.auto_generate_totp = auto_generate_totp
        self.cookie_file = Path(cookie_file) if cookie_file else None
        
        # 会话和认证状态
        self.session = None
        self.auth_cookie = None
        self.two_factor_token = None
        self.is_authenticated = False
        
        # 加载已保存的Cookie
        self._load_saved_cookie()
        
        logger.info(f"VRChat API客户端初始化完成")
        logger.info(f"Cookie文件: {self.cookie_file}")
        logger.info(f"TOTP自动生成: {auto_generate_totp}")
    
    def _load_saved_cookie(self):
        """加载保存的Cookie"""
        try:
            if self.cookie_file and self.cookie_file.exists():
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookie_data = json.load(f)
                
                self.auth_cookie = cookie_data.get('auth_cookie')
                saved_time = cookie_data.get('saved_at')
                
                if self.auth_cookie and saved_time:
                    # 检查Cookie是否过期（假设有效期为30天）
                    import time
                    from datetime import datetime, timedelta
                    
                    saved_dt = datetime.fromisoformat(saved_time)
                    if datetime.now() - saved_dt < timedelta(days=30):
                        logger.info("找到有效的已保存Cookie")
                        self.is_authenticated = True
                    else:
                        logger.info("Cookie已过期")
                        self.auth_cookie = None
                else:
                    logger.info("Cookie文件格式不正确")
            else:
                logger.info("未找到已保存的Cookie")
                
        except Exception as e:
            logger.warning(f"加载保存的Cookie失败: {e}")
            self.auth_cookie = None
    
    def _save_cookie(self):
        """保存Cookie到文件"""
        try:
            if self.cookie_file and self.auth_cookie:
                cookie_data = {
                    'auth_cookie': self.auth_cookie,
                    'username': self.username,
                    'saved_at': datetime.now().isoformat()
                }
                
                # 确保目录存在
                self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookie_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Cookie已保存到: {self.cookie_file}")
                
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
    
    async def _create_session(self):
        """创建HTTP会话"""
        if self.session is None:
            connector = None
            if self.proxy_config:
                connector = aiohttp.TCPConnector(
                    ssl=False,
                    use_dns_cache=True,
                    ttl_dns_cache=300
                )
            
            headers = {
                'User-Agent': 'VRC-QQ-Bot/1.0.0 (Linux; Unity 2022.3.6f1)',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
            cookie_jar = aiohttp.CookieJar()
            # 如果已有Cookie，添加到请求头
            if self.auth_cookie:
                cookie_jar.update_cookies(
                    {'auth': self.auth_cookie},
                    URL(self.BASE_URL)
                )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                cookie_jar=cookie_jar,
                headers=headers
            )
            
            if self.proxy_config:
                logger.info(f"已配置代理: {self.proxy_config}")
    
    async def authenticate(self, two_factor_code: Optional[str] = None, 
                          cli_mode: bool = False) -> Tuple[bool, str]:
        """
        认证到VRChat API
        
        Args:
            two_factor_code: 二步验证码（可选）
            cli_mode: 是否为CLI模式（用于交互式输入）
            
        Returns:
            Tuple[bool, str]: (认证成功, 消息)
        """
        try:
            await self._create_session()
            
            # 首先尝试使用已保存的Cookie
            if self.auth_cookie and not two_factor_code:
                logger.info("尝试使用已保存的Cookie进行认证...")
                if await self._test_auth():
                    logger.success("Cookie认证成功！")
                    self.is_authenticated = True
                    return True, "认证成功（使用保存的Cookie）"
                else:
                    logger.info("Cookie认证失败，尝试密码认证...")
                    self.auth_cookie = None
            
            # 密码认证
            logger.info("开始VRChat API密码认证...")

            username = self.username
            password = self.password
            auth_string = f"{quote(username)}:{quote(password)}"
            auth_base64 = base64.b64encode(auth_string.encode()).decode()

            async with self.session.get(
                    f"{self.BASE_URL}/auth/user",
                    headers={
                        "Authorization": "Basic " + auth_base64
                    },
                    proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                logger.debug(f"认证响应状态: {response.status}")
                
                if response.status == 200:
                    # 认证成功
                    cookies = response.cookies
                    if 'auth' in cookies:
                        self.auth_cookie = cookies['auth'].value
                        self._save_cookie()
                    
                    self.is_authenticated = True
                    logger.success("VRChat认证成功！")
                    return True, "认证成功"
                    
                elif response.status == 401:
                    # 需要二步验证
                    error_text = await response.text()
                    logger.warning(f"需要二步验证: {error_text}")
                    
                    if 'requiresTwoFactorAuth' in error_text:
                        return await self._handle_two_factor_auth(two_factor_code, cli_mode)
                    else:
                        error_msg = f"认证失败: {error_text}"
                        logger.error(error_msg)
                        return False, error_msg
                        
                else:
                    error_text = await response.text()
                    error_msg = f"认证请求失败: {response.status} - {error_text}"
                    logger.error(error_msg)
                    return False, error_msg
                    
        except Exception as e:
            logger.exception(f"认证过程中发生错误: {e}")
            return False, f"发生错误: {str(e)}"
    
    async def _test_auth(self) -> bool:
        """测试当前认证是否有效"""
        try:
            if not self.auth_cookie:
                return False
            
            async with self.session.get(
                f"{self.BASE_URL}/auth",
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.debug(f"测试认证失败: {e}")
            return False
    
    async def _handle_two_factor_auth(self, two_factor_code: Optional[str] = None, 
                                     cli_mode: bool = False) -> Tuple[bool, str]:
        """
        处理二步验证
        
        Args:
            two_factor_code: 二步验证码
            cli_mode: 是否为CLI模式
            
        Returns:
            Tuple[bool, str]: (验证成功, 消息)
        """
        try:
            # 如果没有提供验证码，尝试自动生成
            if not two_factor_code and self.totp_secret and self.auto_generate_totp:
                logger.info("使用TOTP密钥生成验证码...")
                totp = pyotp.TOTP(self.totp_secret)
                two_factor_code = totp.now()
                logger.info(f"生成的验证码: {two_factor_code}")
            
            # CLI模式下等待用户输入
            if not two_factor_code and cli_mode:
                logger.info("等待用户输入二步验证码...")
                return False, "需要二步验证码，请在CLI模式下输入"
            
            if not two_factor_code:
                error_msg = "需要二步验证码但未提供"
                logger.error(error_msg)
                return False, error_msg
            
            # 验证二步验证码
            verify_data = {
                'code': two_factor_code,
                'userId': self.username,
            }
            
            async with self.session.post(
                f"{self.BASE_URL}/auth/twofactorauth/otp/verify",
                json=verify_data,
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                response_text = await response.text()
                logger.debug(f"二步验证响应: {response.status} - {response_text}")
                
                if response.status == 200:
                    result = json.loads(response_text)
                    self.two_factor_token = result.get('verified', False)
                    
                    if self.two_factor_token:
                        logger.success("二步验证成功！")
                        # 重新尝试认证
                        return await self._finish_auth()
                    else:
                        error_msg = "二步验证失败"
                        logger.error(error_msg)
                        return False, error_msg
                else:
                    error_msg = f"二步验证请求失败: {response.status} - {response_text}"
                    logger.error(error_msg)
                    return False, error_msg
                    
        except Exception as e:
            logger.exception(f"二步验证过程中发生错误: {e}")
            return False, f"发生错误: {str(e)}"
    
    async def _finish_auth(self) -> Tuple[bool, str]:
        """完成认证流程"""
        try:
            username = self.username
            password = self.password
            auth_string = f"{quote(username)}:{quote(password)}"
            auth_base64 = base64.b64encode(auth_string.encode()).decode()
            
            async with self.session.get(
                f"{self.BASE_URL}/auth/user",
                headers={
                    "Authorization": "Basic " + auth_base64
                },
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                if response.status == 200:
                    cookies = response.cookies
                    if 'auth' in cookies:
                        self.auth_cookie = cookies['auth'].value
                        self._save_cookie()
                    
                    self.is_authenticated = True
                    logger.success("VRChat认证完成！")
                    return True, "认证成功"
                else:
                    error_text = await response.text()
                    error_msg = f"最终认证失败: {response.status} - {error_text}"
                    logger.error(error_msg)
                    return False, error_msg
                    
        except Exception as e:
            logger.exception(f"完成认证时发生错误: {e}")
            return False, f"发生错误: {str(e)}"
    
    async def get_user_info(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        try:
            await self._create_session()
            
            if not self.is_authenticated:
                logger.warning("未认证，尝试重新认证...")
                success, msg = await self.authenticate()
                if not success:
                    logger.error(f"重新认证失败: {msg}")
                    return None
            
            async with self.session.get(
                f"{self.BASE_URL}/users/{user_id}",
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                logger.debug(f"获取用户信息响应: {response.status}")
                
                if response.status == 200:
                    user_info = await response.json()
                    logger.info(f"成功获取用户信息: {user_info.get('displayName', user_id)}")
                    return user_info
                elif response.status == 404:
                    logger.warning(f"用户不存在: {user_id}")
                    return None
                elif response.status == 401:
                    logger.warning("认证过期，尝试重新认证...")
                    self.is_authenticated = False
                    self.auth_cookie = None
                    return await self.get_user_info(user_id)  # 递归调用一次
                else:
                    error_text = await response.text()
                    logger.error(f"获取用户信息失败: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.exception(f"获取用户信息时发生错误: {e}")
            return None
    
    async def add_user_to_group(self, group_id: str, user_id: str, role_id: str) -> Tuple[bool, str]:
        """将用户添加到VRChat群组并分配角色"""
        try:
            await self._create_session()
            
            if not self.is_authenticated:
                logger.warning("未认证，尝试重新认证...")
                success, msg = await self.authenticate()
                if not success:
                    return False, f"认证失败: {msg}"
            
            # 首先检查用户是否在群组中
            is_member = await self._is_user_in_group(group_id, user_id)
            if not is_member:
                invite_result = await self._invite_user_to_group(group_id, user_id)
                if not invite_result[0]:
                    return invite_result
            
            # 分配角色
            role_data = {
                'memberId': user_id,
                'roleId': role_id,
            }
            
            async with self.session.post(
                f"{self.BASE_URL}/groups/{group_id}/roles",
                json=role_data,
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                response_text = await response.text()
                logger.debug(f"分配角色响应: {response.status} - {response_text}")
                
                if response.status == 200:
                    logger.success(f"成功为用户 {user_id} 分配角色 {role_id}")
                    return True, "角色分配成功"
                elif response.status == 429:
                    logger.warning("请求速率过快")
                    return False, "请求速率过快，请稍后再试"
                elif response.status == 403:
                    if "banned" in response_text.lower():
                        return False, "用户已被封禁"
                    else:
                        return False, "权限不足，无法分配角色"
                elif response.status == 404:
                    return False, "群组或用户不存在"
                else:
                    logger.error(f"分配角色失败: HTTP {response.status} - {response_text}")
                    return False, f"分配角色失败: HTTP {response.status}"
                    
        except Exception as e:
            logger.exception(f"分配角色时发生错误: {e}")
            if "Connection reset" in str(e):
                return False, "连接被重置"
            return False, f"发生错误: {str(e)}"
    
    async def _is_user_in_group(self, group_id: str, user_id: str) -> bool:
        """检查用户是否在群组中"""
        try:
            async with self.session.get(
                f"{self.BASE_URL}/groups/{group_id}/members",
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                if response.status == 200:
                    members = await response.json()
                    return any(member.get('userId') == user_id for member in members)
                else:
                    error_text = await response.text()
                    logger.warning(f"无法获取群组成员列表: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"检查群组成员时发生错误: {e}")
            return False
    
    async def _invite_user_to_group(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """邀请用户加入群组"""
        try:
            invite_data = {
                'userId': user_id,
            }
            
            async with self.session.post(
                f"{self.BASE_URL}/groups/{group_id}/invites",
                json=invite_data,
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                response_text = await response.text()
                
                if response.status in [200, 201]:
                    logger.success(f"成功邀请用户 {user_id} 加入群组 {group_id}")
                    return True, "邀请成功"
                else:
                    logger.error(f"邀请用户失败: HTTP {response.status} - {response_text}")
                    return False, f"邀请失败: HTTP {response.status}"
                    
        except Exception as e:
            logger.exception(f"邀请用户时发生错误: {e}")
            return False, f"邀请失败: {str(e)}"
    
    async def remove_user_from_group(self, group_id: str, user_id: str) -> Tuple[bool, str]:
        """从群组中移除用户"""
        try:
            async with self.session.delete(
                f"{self.BASE_URL}/groups/{group_id}/members/{user_id}",
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                response_text = await response.text()
                
                if response.status == 200:
                    logger.success(f"成功从群组 {group_id} 移除用户 {user_id}")
                    return True, "移除成功"
                else:
                    logger.error(f"移除用户失败: HTTP {response.status} - {response_text}")
                    return False, f"移除失败: HTTP {response.status}"
                    
        except Exception as e:
            logger.exception(f"移除用户时发生错误: {e}")
            return False, f"移除失败: {str(e)}"
    
    def validate_user_id(self, user_id: str) -> bool:
        """验证VRChat用户ID格式"""
        pattern = r"usr_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        return bool(re.match(pattern, user_id, re.IGNORECASE))
    
    async def close(self):
        """异步关闭会话"""
        if self.session:
            await self.session.close()
            logger.info("VRChat API客户端已关闭")