"""
QQ Bot管理器
集成Napcat API，处理QQ群相关操作
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
import aiohttp
from loguru import logger
import requests


class QQBotManager:
    """QQ Bot管理器"""
    
    def __init__(self, host: str, port: int, 
                 access_token: Optional[str] = None,
                 webhook_url: Optional[str] = None):
        """
        初始化QQ Bot管理器
        
        Args:
            host: Napcat服务器地址
            port: Napcat服务器端口
            access_token: 访问令牌（可选）
            webhook_url: Webhook地址（可选）
        """
        self.base_url = f"http://{host}:{port}"
        self.access_token = access_token
        self.webhook_url = webhook_url
        
        # HTTP会话
        self.session = requests.Session()
        if access_token:
            self.session.headers.update({
                'Authorization': f'Bearer {access_token}'
            })
        
        # 事件处理器
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        logger.info(f"QQ Bot管理器初始化完成: {self.base_url}")
    
    def send_group_message(self, group_id: int, message: str, 
                          message_type: str = "text") -> bool:
        """
        发送群消息
        
        Args:
            group_id: 群号
            message: 消息内容
            message_type: 消息类型 (text, image, etc.)
            
        Returns:
            bool: 发送成功返回True
        """
        try:
            url = f"{self.base_url}/send_group_msg"
            data = {
                'group_id': group_id,
                'message': message,
                'auto_escape': False
            }
            
            response = self.session.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    logger.info(f"群消息发送成功 [群{group_id}]: {message[:50]}...")
                    return True
                else:
                    logger.error(f"群消息发送失败: {result}")
                    return False
            else:
                logger.error(f"发送群消息请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"发送群消息时发生错误: {e}")
            return False
    
    def send_private_message(self, user_id: int, message: str) -> bool:
        """
        发送私聊消息
        
        Args:
            user_id: QQ号
            message: 消息内容
            
        Returns:
            bool: 发送成功返回True
        """
        try:
            url = f"{self.base_url}/send_private_msg"
            data = {
                'user_id': user_id,
                'message': message,
                'auto_escape': False
            }
            
            response = self.session.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    logger.info(f"私聊消息发送成功 [用户{user_id}]: {message[:50]}...")
                    return True
                else:
                    logger.error(f"私聊消息发送失败: {result}")
                    return False
            else:
                logger.error(f"发送私聊消息请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"发送私聊消息时发生错误: {e}")
            return False
    
    def get_group_member_info(self, group_id: int, user_id: int) -> Optional[Dict]:
        """
        获取群成员信息
        
        Args:
            group_id: 群号
            user_id: QQ号
            
        Returns:
            成员信息字典或None
        """
        try:
            url = f"{self.base_url}/get_group_member_info"
            params = {
                'group_id': group_id,
                'user_id': user_id,
                'no_cache': False
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    return result.get('data')
                else:
                    logger.warning(f"获取群成员信息失败: {result}")
                    return None
            else:
                logger.error(f"获取群成员信息请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.exception(f"获取群成员信息时发生错误: {e}")
            return None
    
    def get_group_member_list(self, group_id: int) -> List[Dict]:
        """
        获取群成员列表
        
        Args:
            group_id: 群号
            
        Returns:
            成员列表
        """
        try:
            url = f"{self.base_url}/get_group_member_list"
            params = {
                'group_id': group_id,
                'no_cache': False
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    return result.get('data', [])
                else:
                    logger.warning(f"获取群成员列表失败: {result}")
                    return []
            else:
                logger.error(f"获取群成员列表请求失败: {response.status_code}")
                return []
                
        except Exception as e:
            logger.exception(f"获取群成员列表时发生错误: {e}")
            return []
    
    def handle_group_request(self, group_id: int, user_id: int, 
                            comment: str, approve: bool) -> bool:
        """
        处理入群申请
        
        Args:
            group_id: 群号
            user_id: 申请人QQ号
            comment: 申请备注
            approve: 是否批准
            
        Returns:
            bool: 处理成功返回True
        """
        try:
            url = f"{self.base_url}/set_group_add_request"
            data = {
                'flag': f"{group_id}_{user_id}_{comment}",
                'type': 'add',
                'approve': approve,
                'reason': "自动审批通过" if approve else "自动审批拒绝"
            }
            
            response = self.session.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    logger.info(f"入群申请处理成功 [群{group_id}] [用户{user_id}] 批准: {approve}")
                    return True
                else:
                    logger.error(f"入群申请处理失败: {result}")
                    return False
            else:
                logger.error(f"处理入群申请请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"处理入群申请时发生错误: {e}")
            return False
    
    def kick_group_member(self, group_id: int, user_id: int, 
                         reject_add_request: bool = False) -> bool:
        """
        踢出群成员
        
        Args:
            group_id: 群号
            user_id: 成员QQ号
            reject_add_request: 是否拒绝再次申请
            
        Returns:
            bool: 操作成功返回True
        """
        try:
            url = f"{self.base_url}/set_group_kick"
            data = {
                'group_id': group_id,
                'user_id': user_id,
                'reject_add_request': reject_add_request
            }
            
            response = self.session.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    logger.info(f"踢出群成员成功 [群{group_id}] [用户{user_id}]")
                    return True
                else:
                    logger.error(f"踢出群成员失败: {result}")
                    return False
            else:
                logger.error(f"踢出群成员请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.exception(f"踢出群成员时发生错误: {e}")
            return False
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型 (group_request, group_increase, etc.)
            handler: 处理函数
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"注册事件处理器: {event_type}")
    
    def process_event(self, event_data: Dict):
        """
        处理接收到的QQ事件
        
        Args:
            event_data: 事件数据
        """
        try:
            event_type = event_data.get('post_type')
            logger.info(f"接收到QQ事件: {event_type}")
            logger.debug(f"事件数据: {event_data}")
            
            # 调用对应的事件处理器
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        handler(event_data)
                    except Exception as e:
                        logger.exception(f"事件处理器执行失败: {e}")
                        
        except Exception as e:
            logger.exception(f"处理事件时发生错误: {e}")
    
    def get_login_info(self) -> Optional[Dict]:
        """
        获取登录信息
        
        Returns:
            登录信息字典或None
        """
        try:
            url = f"{self.base_url}/get_login_info"
            response = self.session.get(url)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    return result.get('data')
                else:
                    logger.warning(f"获取登录信息失败: {result}")
                    return None
            else:
                logger.error(f"获取登录信息请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.exception(f"获取登录信息时发生错误: {e}")
            return None
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
            logger.info("QQ Bot管理器已关闭")