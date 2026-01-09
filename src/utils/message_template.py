"""
消息模板系统
处理消息模板和变量替换
"""

import re
from typing import Dict, Optional, Any
from datetime import datetime
from loguru import logger


class MessageTemplate:
    """消息模板处理器"""
    
    # 支持的变量
    SUPPORTED_VARIABLES = {
        # VRChat相关
        '%vrc_username%': 'VRChat用户名',
        '%vrc_userid%': 'VRChat用户ID',
        '%vrc_displayname%': 'VRChat显示名称',
        
        # QQ相关
        '%qq_user_num%': 'QQ号',
        '%qq_nickname%': 'QQ昵称',
        '%qq_group_name%': '群名称',
        '%qq_group_id%': '群号',
        
        # 操作相关
        '%execute_user%': '执行操作的用户',
        '%operator_name%': '操作者名称',
        '%operation_time%': '操作时间',
        
        # 系统相关
        '%app_name%': '应用名称',
        '%app_version%': '应用版本',
        '%error_reason%': '错误原因',
        '%status%': '操作状态',
        
        # 群组相关
        '%vrc_group_name%': 'VRChat群组名称',
        '%vrc_group_id%': 'VRChat群组ID',
        '%vrc_role_name%': 'VRChat角色名称',
        '%vrc_role_id%': 'VRChat角色ID',
    }
    
    def __init__(self, templates_config: Dict[str, str]):
        """
        初始化消息模板处理器
        
        Args:
            templates_config: 模板配置字典
        """
        self.templates = templates_config
        logger.info(f"消息模板系统初始化完成，共 {len(templates_config)} 个模板")
    
    def render(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        渲染消息模板
        
        Args:
            template_name: 模板名称
            variables: 变量字典
            
        Returns:
            渲染后的消息
        """
        try:
            # 获取模板
            template = self.templates.get(template_name, '')
            if not template:
                logger.warning(f"模板不存在: {template_name}")
                return ""
            
            # 渲染模板
            rendered = self._render_template(template, variables)
            
            logger.debug(f"模板渲染成功: {template_name}")
            logger.debug(f"变量: {variables}")
            logger.debug(f"结果: {rendered[:100]}...")
            
            return rendered
            
        except Exception as e:
            logger.exception(f"模板渲染失败: {e}")
            return f"模板渲染失败: {str(e)}"
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        渲染模板字符串
        
        Args:
            template: 模板字符串
            variables: 变量字典
            
        Returns:
            渲染后的字符串
        """
        result = template
        
        # 替换所有支持的变量
        for var_name, var_desc in self.SUPPORTED_VARIABLES.items():
            if var_name in result:
                # 获取变量值
                var_key = var_name.strip('%')
                var_value = variables.get(var_key, '')
                
                # 转换为字符串
                if var_value is None:
                    var_value = ""
                elif not isinstance(var_value, str):
                    var_value = str(var_value)
                
                # 替换
                result = result.replace(var_name, var_value)
        
        return result
    
    def get_template(self, template_name: str) -> str:
        """
        获取原始模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板字符串
        """
        return self.templates.get(template_name, '')
    
    def update_template(self, template_name: str, template_content: str) -> bool:
        """
        更新模板
        
        Args:
            template_name: 模板名称
            template_content: 模板内容
            
        Returns:
            bool: 更新成功返回True
        """
        try:
            self.templates[template_name] = template_content
            logger.info(f"模板更新成功: {template_name}")
            return True
            
        except Exception as e:
            logger.exception(f"模板更新失败: {e}")
            return False
    
    def validate_variables(self, variables: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证变量是否有效
        
        Args:
            variables: 变量字典
            
        Returns:
            (是否有效, 缺失的变量列表)
        """
        missing_vars = []
        
        for var_name, var_desc in self.SUPPORTED_VARIABLES.items():
            var_key = var_name.strip('%')
            if var_key not in variables:
                missing_vars.append(var_key)
        
        is_valid = len(missing_vars) == 0
        return is_valid, missing_vars
    
    def get_supported_variables(self) -> Dict[str, str]:
        """
        获取支持的变量列表
        
        Returns:
            变量字典 {变量名: 描述}
        """
        return self.SUPPORTED_VARIABLES.copy()
    
    @staticmethod
    def create_welcome_variables(qq_id: int, vrc_user_id: str, 
                                vrc_username: str, group_id: int,
                                group_name: str = "") -> Dict[str, Any]:
        """
        创建欢迎消息的变量
        
        Args:
            qq_id: QQ号
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
            group_id: 群号
            group_name: 群名称
            
        Returns:
            变量字典
        """
        return {
            'qq_user_num': qq_id,
            'vrc_userid': vrc_user_id,
            'vrc_username': vrc_username,
            'qq_group_id': group_id,
            'qq_group_name': group_name,
            'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'execute_user': qq_id,
            'status': '成功'
        }
    
    @staticmethod
    def create_leave_variables(qq_id: int, vrc_user_id: str, 
                              vrc_username: str, group_id: int,
                              group_name: str = "") -> Dict[str, Any]:
        """
        创建退群消息的变量
        
        Args:
            qq_id: QQ号
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
            group_id: 群号
            group_name: 群名称
            
        Returns:
            变量字典
        """
        return {
            'qq_user_num': qq_id,
            'vrc_userid': vrc_user_id,
            'vrc_username': vrc_username,
            'qq_group_id': group_id,
            'qq_group_name': group_name,
            'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'execute_user': qq_id,
            'status': '离开'
        }
    
    @staticmethod
    def create_error_variables(error_reason: str, 
                              operator_qq: Optional[int] = None) -> Dict[str, Any]:
        """
        创建错误消息的变量
        
        Args:
            error_reason: 错误原因
            operator_qq: 操作者QQ号
            
        Returns:
            变量字典
        """
        return {
            'error_reason': error_reason,
            'operator_name': operator_qq or '系统',
            'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': '失败'
        }
    
    @staticmethod
    def create_manual_bind_variables(qq_id: int, vrc_user_id: str,
                                   vrc_username: str, 
                                   operator_qq: int) -> Dict[str, Any]:
        """
        创建手动绑定消息的变量
        
        Args:
            qq_id: 目标QQ号
            vrc_user_id: VRChat用户ID
            vrc_username: VRChat用户名
            operator_qq: 操作者QQ号
            
        Returns:
            变量字典
        """
        return {
            'qq_user_num': qq_id,
            'vrc_userid': vrc_user_id,
            'vrc_username': vrc_username,
            'execute_user': operator_qq,
            'operator_name': operator_qq,
            'operation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': '成功'
        }


# 预定义的常用消息模板
DEFAULT_TEMPLATES = {
    'welcome_message': '''欢迎 %vrc_username% 加入本群！
您的VRChat用户ID: %vrc_userid%
已自动为您分配角色，祝您游戏愉快！''',
    
    'leave_message': '''用户 %vrc_username% (%vrc_userid%) 已离开群组''',
    
    'review_request': '''有新的入群申请需要审查：
QQ号: %qq_user_num%
VRChat用户ID: %vrc_userid%
请在VRChat中确认用户信息''',
    
    'role_assignment_failed': '''为用户 %vrc_username% (%vrc_userid%) 分配角色失败
失败原因: %error_reason%
请管理员手动处理''',
    
    'invalid_format': '''您的入群申请格式不正确
请提供正确的VRChat用户ID格式：usr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx''',
    
    'manual_bind_success': '''绑定成功！
QQ: %qq_user_num%
VRChat: %vrc_username% (%vrc_userid%)''',
    
    'manual_unbind_success': '''解绑成功！
QQ: %qq_user_num%
VRChat: %vrc_username% (%vrc_userid%)''',
    
    'user_not_found': '''未找到VRChat用户：%vrc_userid%
请检查用户ID是否正确''',
    
    'user_banned': '''用户 %vrc_username% 已被封禁，无法分配角色''',
    
    'rate_limit': '''操作过于频繁，请稍后再试''',
    
    'permission_denied': '''权限不足，无法执行此操作''',
    
    'connection_error': '''连接VRChat服务器失败，请检查网络连接''',
}