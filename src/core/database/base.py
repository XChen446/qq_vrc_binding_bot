from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class BaseDatabase(ABC):
    """数据库抽象基类，定义所有后端必须实现的接口"""
    
    @abstractmethod
    def bind_user(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, bind_type: str = "manual", group_id: Optional[int] = None) -> bool:
        """
        建立 QQ 号与 VRChat 账号的绑定关系
        :param qq_id: 用户的 QQ 号
        :param vrc_user_id: 用户的 VRChat 唯一 ID (usr_...)
        :param vrc_display_name: 用户的 VRChat 显示名称
        :param bind_type: 绑定类型 (manual/auto)
        :param group_id: 来源群组 ID (可选)
        :return: 绑定是否成功
        """
        pass


    @abstractmethod
    def unbind_user_from_group(self, group_id: int, qq_id: int) -> bool:
        """
        从指定群聊中移除绑定记录，并更新全局记录来源
        :param group_id: 群号
        :param qq_id: QQ号
        :return: 是否成功
        """
        pass

    @abstractmethod
    def unbind_user_globally(self, qq_id: int) -> bool:
        """
        全局解绑用户（从全局表删除）
        :param qq_id: QQ号
        :return: 是否成功
        """
        pass

    @abstractmethod
    def get_group_bindings(self, group_id: int) -> List[Dict]:
        """
        获取指定群的所有绑定记录
        :param group_id: 群号
        :return: 绑定记录列表
        """
        pass

    @abstractmethod
    def get_group_member_binding(self, group_id: int, qq_id: int) -> Optional[Dict]:
        """
        获取指定群成员的绑定记录
        :param group_id: 群号
        :param qq_id: QQ号
        :return: 绑定记录字典
        """
        pass


    @abstractmethod
    def get_qq_by_vrc_id(self, vrc_user_id: str) -> Optional[int]:
        """
        通过 VRChat ID 反查绑定的 QQ 号
        :param vrc_user_id: VRChat 唯一 ID
        :return: 绑定的 QQ 号，若未绑定则返回 None
        """
        pass

    @abstractmethod
    def get_binding(self, qq_id: int) -> Optional[Dict]:
        """
        通过 QQ 号查询完整的绑定记录
        :param qq_id: 用户的 QQ 号
        :return: 包含绑定信息的字典，若未绑定则返回 None
        """
        pass


    @abstractmethod
    def get_all_bindings(self) -> List[Dict]:
        """
        获取数据库中所有的绑定记录列表
        :return: 包含所有绑定信息的字典列表
        """
        pass

    @abstractmethod
    def search_global_bindings(self, query: str) -> List[Dict]:
        """
        全局搜索绑定记录
        :param query: 搜索关键词 (QQ号/VRC ID/VRC 显示名称)
        :return: 匹配的绑定记录列表
        """
        pass

    @abstractmethod
    def add_verification(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, code: str) -> bool:
        """
        添加验证记录
        :param qq_id: QQ号
        :param vrc_user_id: VRChat ID
        :param vrc_display_name: VRChat 显示名称
        :param code: 验证码
        :return: 是否成功
        """
        pass

    @abstractmethod
    def get_verification(self, qq_id: int) -> Optional[Dict]:
        """
        获取验证记录
        :param qq_id: QQ号
        :return: 验证记录字典 {qq_id, vrc_user_id, vrc_display_name, code, created_at}
        """
        pass

    @abstractmethod
    def delete_verification(self, qq_id: int) -> bool:
        """
        删除验证记录
        :param qq_id: QQ号
        :return: 是否成功
        """
        pass

    @abstractmethod
    def mark_verification_expired(self, qq_id: int) -> bool:
        """
        标记验证码为已过期
        :param qq_id: QQ号
        :return: 是否成功
        """
        pass

    @abstractmethod
    def expire_outdated_verifications(self, expiry_seconds: int) -> int:
        """
        批量标记过期的验证记录
        :param expiry_seconds: 有效期秒数
        :return: 影响的行数
        """
        pass

    @abstractmethod
    def set_group_vrc_group_id(self, group_id: int, vrc_group_id: str) -> bool:
        """
        设置群组绑定的 VRChat 群组 ID
        :param group_id: QQ群号
        :param vrc_group_id: VRChat 群组 ID
        :return: 是否成功
        """
        pass

    @abstractmethod
    def get_group_vrc_group_id(self, group_id: int) -> Optional[str]:
        """
        获取群组绑定的 VRChat 群组 ID
        :param group_id: QQ群号
        :return: VRChat 群组 ID
        """
        pass

    @abstractmethod
    def delete_group_vrc_group_id(self, group_id: int) -> bool:
        """
        删除群组绑定的 VRChat 群组 ID
        :param group_id: QQ群号
        :return: 是否成功
        """
        pass

    @abstractmethod
    def set_group_setting(self, group_id: int, setting_name: str, setting_value: str) -> bool:
        """
        设置群组特定配置
        :param group_id: 群号
        :param setting_name: 设置名称
        :param setting_value: 设置值
        :return: 是否成功
        """
        pass

    @abstractmethod
    def get_group_setting(self, group_id: int, setting_name: str) -> Optional[str]:
        """
        获取群组特定配置
        :param group_id: 群号
        :param setting_name: 设置名称
        :return: 设置值，若不存在则返回None
        """
        pass

    @abstractmethod
    def add_global_verification(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, verified_by: str = "system") -> bool:
        """
        添加全局验证记录（用户已完成验证）
        :param qq_id: QQ号
        :param vrc_user_id: VRChat ID
        :param vrc_display_name: VRChat 显示名称
        :param verified_by: 验证来源
        :return: 是否成功
        """
        pass

    @abstractmethod
    def get_global_verification(self, qq_id: int) -> Optional[Dict]:
        """
        获取全局验证记录
        :param qq_id: QQ号
        :return: 验证记录字典
        """
        pass

    @abstractmethod
    def get_group_binding_with_global_fallback(self, group_id: int, qq_id: int) -> Optional[Dict]:
        """
        获取群组绑定记录，如果群组中没有则从全局验证获取
        :param group_id: 群号
        :param qq_id: QQ号
        :return: 绑定记录字典
        """
        pass

    @abstractmethod
    def search_bindings(self, query: str) -> List[Dict]:
        """
        搜索绑定记录（全局）
        :param query: 搜索关键词
        :return: 匹配的绑定记录列表
        """
        pass

    @abstractmethod
    def get_pending_vrc_info(self, user_id: int) -> Optional[Dict]:
        """
        获取用户待处理的VRChat信息
        :param user_id: QQ用户ID
        :return: VRChat信息字典
        """
        pass