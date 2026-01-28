import os
import logging
import asyncio
import time
from typing import Optional, Dict, Any, List
import vrchatapi
from vrchatapi.api import authentication_api, users_api, groups_api
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.configuration import Configuration
from vrchatapi.rest import ApiException
from vrchatapi import ApiClient

logger = logging.getLogger("VRChatAPI")

class VRCApiClient:
    def __init__(self, config, cookie_path: str = "data/cookies.txt"):
        self.config = config
        self.cookie_path = cookie_path
        
        # 设置API配置
        username = getattr(config, 'username', '') or (config.get('username') if hasattr(config, 'get') else '')
        password = getattr(config, 'password', '') or (config.get('password') if hasattr(config, 'get') else '')
        
        self.configuration = Configuration()
        if username and password:
            self.configuration.username = username
            self.configuration.password = password
        
        # 如果提供了代理，则设置代理
        proxy = getattr(config, 'proxy', '') or (config.get('proxy') if hasattr(config, 'get') else '')
        if proxy:
            self.configuration.proxy = proxy

        # 设置User-Agent，从配置中获取或使用默认值
        user_agent = getattr(config, 'user_agent', '') or (config.get('user_agent', '') if hasattr(config, 'get') else '')
        if user_agent:
            self.configuration.user_agent = user_agent
        else:
            # 设置默认User-Agent，遵循VRChat API要求的格式
            self.configuration.user_agent = "Q2VBindBot/1.2 (chen@xchen.link, MiaobaiQWQ@github.com)"

        # 使用ApiClient包装配置以支持异步调用
        api_client = ApiClient(self.configuration)
        
        # 重要：更新ApiClient的默认headers以确保User-Agent被正确设置
        api_client.default_headers['User-Agent'] = self.configuration.user_agent

        # 初始化API实例
        self.authentication_api = authentication_api.AuthenticationApi(api_client)
        self.users_api = users_api.UsersApi(api_client)
        self.groups_api = groups_api.GroupsApi(api_client)
        
        # 延迟初始化认证类，避免构造时的导入问题
        self._auth = None
        
        # 请求限流设置
        self._last_request_time = {}
        self._min_request_interval = 0.1  # 最小请求间隔（秒）

    @property
    def auth(self):
        """懒加载认证实例"""
        if self._auth is None:
            from .auth import VRCAuth
            self._auth = VRCAuth(self, self.configuration)
        return self._auth

    async def close(self) -> None:
        """关闭连接"""
        # 在新库中可能不需要特殊关闭操作
        pass

    async def _rate_limit(self, endpoint: str):
        """请求限流"""
        current_time = time.time()
        if endpoint in self._last_request_time:
            elapsed = current_time - self._last_request_time[endpoint]
            if elapsed < self._min_request_interval:
                await asyncio.sleep(self._min_request_interval - elapsed)
        
        self._last_request_time[endpoint] = time.time()

    async def _make_authenticated_request(self, func, *args, max_retries=3, **kwargs):
        """带认证和重试机制的请求包装器"""
        for attempt in range(max_retries):
            try:
                # 应用请求限流
                await self._rate_limit(func.__name__)
                
                # 执行API调用 - 使用线程池执行器来实现异步调用
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: func(*args, **kwargs)
                )
                return result
            except ApiException as e:
                if e.status == 401:
                    # 认证失败，尝试重新登录
                    logger.warning(f"API认证失败 (401) on attempt {attempt + 1}, attempting re-authentication...")
                    logger.debug(f"认证失败详情: User={getattr(self.config, 'username', 'Unknown')}, Attempt={attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:  # 不在最后一次尝试时重试
                        auth_success = await self.auth.login()
                        if auth_success:
                            continue  # 重试请求
                        else:
                            logger.error(f"重新认证失败: User={getattr(self.config, 'username', 'Unknown')}")
                            break
                    else:
                        logger.error(f"API认证失败，已达最大重试次数: User={getattr(self.config, 'username', 'Unknown')}, Error: {e}", exc_info=True)
                        break
                elif e.status == 429:
                    # 请求频率过高，等待后重试
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"请求频率过高 (429), 等待 {wait_time} 秒后重试...")
                    logger.debug(f"频率限制详情: Endpoint={func.__name__}, Attempt={attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    if attempt < max_retries - 1:
                        continue
                else:
                    logger.error(f"API错误 ({e.status}): {e}")
                    logger.debug(f"API错误详情: Endpoint={func.__name__}, Status={e.status}, Reason={e.reason}", exc_info=True)
                    if attempt == max_retries - 1:
                        raise e  # 如果是最后一次尝试，抛出异常
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            except asyncio.TimeoutError:
                logger.warning(f"请求超时 on attempt {attempt + 1}")
                logger.debug(f"超时详情: Endpoint={func.__name__}, Attempt={attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise
            except ConnectionError:
                logger.warning(f"连接错误 on attempt {attempt + 1}")
                logger.debug(f"连接错误详情: Endpoint={func.__name__}, Attempt={attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise
            except Exception as e:
                logger.error(f"未知错误: {e}")
                logger.debug(f"未知错误详情: Endpoint={func.__name__}, Args={args}, Kwargs={kwargs}", exc_info=True)
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)
        
        return None

    async def search_users(self, query: str) -> List[Dict[str, Any]]:
        """搜索用户"""
        try:
            # 如果是usr_开头的ID，直接获取用户
            if query.startswith("usr_"):
                user = await self.get_user(query)
                return [user] if user else []
            
            # 否则进行搜索
            api_response = await self._make_authenticated_request(
                self.users_api.get_users,
                search=query, n=10,
                async_req=True
            )
            
            if not api_response:
                return []
                
            users = []
            for user in api_response:
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "displayName": user.display_name,
                    "currentAvatarImageUrl": user.current_avatar_image_url,
                    "currentAvatarThumbnailImageUrl": user.current_avatar_thumbnail_image_url,
                    "status": user.status,
                    "statusDescription": user.status_description,
                    "bio": user.bio,
                    "isBanned": user.is_banned,
                    "isBoopingEnabled": user.is_booping_enabled,
                    "date_joined": user.date_joined,
                    "last_platform": user.last_platform,
                    "allow_avatar_copying": user.allow_avatar_copying,
                    "tags": user.tags,
                    "developer_type": user.developer_type,
                    "moderation_status": user.moderation_status,
                    "badges": user.badges,
                    "thumbnail_url": user.thumbnail_url,
                    "profile_pic_override": user.profile_pic_override,
                    "user_icon": user.user_icon,
                    "location": user.location,
                    "home_location": user.home_location,
                    "state": user.state
                }
                users.append(user_dict)
            return users
        except Exception as e:
            logger.error(f"搜索用户失败: Query={query}, Error: {e}", exc_info=True)
            return []

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            user = await self._make_authenticated_request(
                self.users_api.get_user,
                user_id=user_id,
                async_req=True
            )
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "displayName": user.display_name,
                    "currentAvatarImageUrl": user.current_avatar_image_url,
                    "currentAvatarThumbnailImageUrl": user.current_avatar_thumbnail_image_url,
                    "status": user.status,
                    "statusDescription": user.status_description,
                    "bio": user.bio,
                    "isBanned": user.is_banned,
                    "isBoopingEnabled": user.is_booping_enabled,
                    "date_joined": user.date_joined,
                    "last_platform": user.last_platform,
                    "allow_avatar_copying": user.allow_avatar_copying,
                    "tags": user.tags,
                    "developer_type": user.developer_type,
                    "moderation_status": user.moderation_status,
                    "badges": user.badges,
                    "thumbnail_url": user.thumbnail_url,
                    "profile_pic_override": user.profile_pic_override,
                    "user_icon": user.user_icon,
                    "location": user.location,
                    "home_location": user.home_location,
                    "state": user.state
                }
            return None
        except Exception as e:
            logger.error(f"获取用户信息失败: UserID={user_id}, Error: {e}", exc_info=True)
            return None

    # ==================== 群组相关接口 ====================

    async def get_group_member(self, group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取群组成员信息"""
        try:
            member = await self._make_authenticated_request(
                self.groups_api.get_group_member,
                group_id=group_id, 
                user_id=user_id,
                async_req=True
            )
            if member:
                return {
                    "userId": member.user_id,
                    "groupId": member.group_id,
                    "isRepresenting": member.is_representing,
                    "isVisible": member.is_visible,
                    "managerNotes": member.manager_notes,
                    "roleIds": member.role_ids,
                    "roles": member.roles,
                    "permissions": member.permissions,
                    "createdAt": member.created_at,
                    "bannedAt": member.banned_at,
                    "acceptedAt": member.accepted_at,
                    "isSubscribedToAnnouncements": member.is_subscribed_to_announcements,
                    "membershipStatus": member.membership_status,
                    "isPending": member.is_pending,
                    "isVisible": member.is_visible,
                    "hasBioLink": member.has_bio_link,
                    "profilePicOverride": member.profile_pic_override,
                    "profilePicOverrideThumbnail": member.profile_pic_override_thumbnail
                }
            return None
        except Exception as e:
            logger.error(f"获取群组成员信息失败: {e}")
            return None

    async def add_group_role(self, group_id: str, user_id: str, role_id: str) -> Optional[Any]:
        """添加群组角色"""
        try:
            response = await self._make_authenticated_request(
                self.groups_api.add_group_role,
                group_id=group_id,
                user_id=user_id,
                json_role_id=role_id,
                async_req=True
            )
            return response
        except Exception as e:
            logger.error(f"添加群组角色失败: {e}")
            return None

    async def get_group_instances(self, group_id: str) -> Optional[Any]:
        """获取群组实例"""
        try:
            # 尝试获取群组信息作为替代
            group = await self._make_authenticated_request(
                self.groups_api.get_group,
                group_id=group_id,
                async_req=True
            )
            if group:
                return [{
                    "id": group.id,
                    "name": group.name,
                    "shortCode": group.short_code,
                    "discriminator": group.discriminator,
                    "description": group.description,
                    "ownerId": group.owner_id,
                    "public": group.public,
                    "verified": group.verified,
                    "featured": group.featured,
                    "iconUrl": group.icon_url,
                    "bannerUrl": group.banner_url,
                    "privacy": group.privacy,
                    "rules": group.rules,
                    "links": group.links,
                    "instanceCount": 0,  # 无法直接获取实例数
                    "memberCount": group.member_count
                }]
            return []
        except Exception as e:
            logger.error(f"获取群组实例失败: {e}")
            return None

    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """获取群组信息"""
        try:
            group = await self._make_authenticated_request(
                self.groups_api.get_group,
                group_id=group_id,
                async_req=True
            )
            if group:
                return {
                    "id": group.id,
                    "name": group.name,
                    "shortCode": group.short_code,
                    "discriminator": group.discriminator,
                    "description": group.description,
                    "ownerId": group.owner_id,
                    "public": group.public,
                    "verified": group.verified,
                    "featured": group.featured,
                    "iconUrl": group.icon_url,
                    "bannerUrl": group.banner_url,
                    "privacy": group.privacy,
                    "rules": group.rules,
                    "links": group.links,
                    "memberCount": group.member_count,
                    "memberCountSyncedAt": group.member_count_synced_at,
                    "gallery": group.gallery,
                    "isVerified": group.is_verified,
                    "isFeatured": group.is_featured,
                    "isPublic": group.is_public
                }
            return None
        except Exception as e:
            logger.error(f"获取群组信息失败: {e}")
            return None