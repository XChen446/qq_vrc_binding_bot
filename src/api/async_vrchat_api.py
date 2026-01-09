"""
异步VRChat API客户端
用于处理大量并发请求
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
from loguru import logger
import pyotp


class AsyncVRChatAPIClient:
    """异步VRChat API客户端"""
    
    BASE_URL = "https://api.vrchat.cloud/api/1"
    
    def __init__(self, username: str, password: str, 
                 proxy_config: Optional[Dict] = None,
                 totp_secret: Optional[str] = None,
                 api_key: str = "JlE5Jldo5JibnkqO"):
        """
        初始化异步VRChat API客户端
        
        Args:
            username: VRChat用户名
            password: VRChat密码
            proxy_config: 代理配置
            totp_secret: TOTP密钥
            api_key: VRChat API密钥
        """
        self.username = username
        self.password = password
        self.api_key = api_key
        self.proxy_config = proxy_config or {}
        self.totp_secret = totp_secret
        
        self.auth_cookie = None
        self.two_factor_token = None
        
        # 连接器配置
        connector = None
        if self.proxy_config:
            connector = aiohttp.TCPConnector(
                ssl=False,
                use_dns_cache=True,
                ttl_dns_cache=300
            )
        
        # 创建会话
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                'User-Agent': 'VRC-QQ-Bot/1.0.0 (Linux; Unity 2022.3.6f1)',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
        )
        
        # 设置代理
        if self.proxy_config:
            logger.info(f"已配置代理: {self.proxy_config}")
    
    async def authenticate(self, two_factor_code: Optional[str] = None) -> bool:
        """
        异步认证到VRChat API
        
        Args:
            two_factor_code: 二步验证码
            
        Returns:
            bool: 认证成功返回True
        """
        try:
            logger.info("开始VRChat API异步认证...")
            
            auth_data = {
                'userId': self.username,
                'password': self.password,
            }
            
            async with self.session.post(
                f"{self.BASE_URL}/auth/user",
                json=auth_data,
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                logger.debug(f"认证响应状态: {response.status}")
                
                if response.status == 200:
                    # 获取认证Cookie
                    cookies = response.cookies
                    if 'auth' in cookies:
                        self.auth_cookie = cookies['auth'].value
                    
                    logger.success("VRChat认证成功！")
                    return True
                    
                elif response.status == 401:
                    # 需要二步验证
                    error_text = await response.text()
                    logger.warning(f"需要二步验证: {error_text}")
                    
                    if 'requiresTwoFactorAuth' in error_text:
                        return await self._handle_two_factor_auth(two_factor_code)
                    else:
                        logger.error(f"认证失败: {error_text}")
                        return False
                        
                else:
                    error_text = await response.text()
                    logger.error(f"认证请求失败: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"认证过程中发生错误: {e}")
            return False
    
    async def _handle_two_factor_auth(self, two_factor_code: Optional[str] = None) -> bool:
        """
        异步处理二步验证
        
        Args:
            two_factor_code: 二步验证码
            
        Returns:
            bool: 验证成功返回True
        """
        try:
            # 自动生成验证码
            if not two_factor_code and self.totp_secret:
                logger.info("使用TOTP密钥生成验证码...")
                totp = pyotp.TOTP(self.totp_secret)
                two_factor_code = totp.now()
                logger.info(f"生成的验证码: {two_factor_code}")
            
            if not two_factor_code:
                logger.error("需要二步验证码但未提供")
                return False
            
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
                        return await self._finish_auth()
                    else:
                        logger.error("二步验证失败")
                        return False
                else:
                    logger.error(f"二步验证请求失败: {response.status} - {response_text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"二步验证过程中发生错误: {e}")
            return False
    
    async def _finish_auth(self) -> bool:
        """
        异步完成认证流程
        
        Returns:
            bool: 认证成功返回True
        """
        try:
            auth_data = {
                'userId': self.username,
                'password': self.password,
            }
            
            async with self.session.post(
                f"{self.BASE_URL}/auth/user",
                json=auth_data,
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                if response.status == 200:
                    cookies = response.cookies
                    if 'auth' in cookies:
                        self.auth_cookie = cookies['auth'].value
                    
                    logger.success("VRChat认证完成！")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"最终认证失败: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"完成认证时发生错误: {e}")
            return False
    
    async def get_user_info(self, user_id: str) -> Optional[Dict]:
        """
        异步获取用户信息
        
        Args:
            user_id: VRChat用户ID
            
        Returns:
            用户信息字典或None
        """
        try:
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
                else:
                    error_text = await response.text()
                    logger.error(f"获取用户信息失败: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.exception(f"获取用户信息时发生错误: {e}")
            return None
    
    async def add_user_to_group(self, group_id: str, user_id: str, role_id: str) -> Tuple[bool, str]:
        """
        异步将用户添加到VRChat群组并分配角色
        
        Args:
            group_id: VRChat群组ID
            user_id: VRChat用户ID
            role_id: 角色ID
            
        Returns:
            (成功, 消息) 元组
        """
        try:
            # 检查用户是否在群组中
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
        """
        异步检查用户是否在群组中
        
        Args:
            group_id: 群组ID
            user_id: 用户ID
            
        Returns:
            bool: 用户在群组中返回True
        """
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
        """
        异步邀请用户加入群组
        
        Args:
            group_id: 群组ID
            user_id: 用户ID
            
        Returns:
            (成功, 消息) 元组
        """
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
        """
        异步从群组中移除用户
        
        Args:
            group_id: 群组ID
            user_id: 用户ID
            
        Returns:
            (成功, 消息) 元组
        """
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
    
    async def get_group_info(self, group_id: str) -> Optional[Dict]:
        """
        异步获取群组信息
        
        Args:
            group_id: 群组ID
            
        Returns:
            群组信息字典或None
        """
        try:
            async with self.session.get(
                f"{self.BASE_URL}/groups/{group_id}",
                params={'apiKey': self.api_key},
                proxy=self.proxy_config.get('https') if self.proxy_config else None
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"获取群组信息失败: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.exception(f"获取群组信息时发生错误: {e}")
            return None
    
    def validate_user_id(self, user_id: str) -> bool:
        """
        验证VRChat用户ID格式
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 格式正确返回True
        """
        pattern = r"usr_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        return bool(re.match(pattern, user_id, re.IGNORECASE))
    
    async def close(self):
        """异步关闭会话"""
        if self.session:
            await self.session.close()