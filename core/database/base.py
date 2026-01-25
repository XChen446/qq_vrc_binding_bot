from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class BaseDatabase(ABC):
    """数据库抽象基类，定义所有后端必须实现的接口"""
    
    @abstractmethod
    def bind_user(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, bind_type: str = "manual") -> bool:
        """
        建立 QQ 号与 VRChat 账号的绑定关系
        :param qq_id: 用户的 QQ 号
        :param vrc_user_id: 用户的 VRChat 唯一 ID (usr_...)
        :param vrc_display_name: 用户的 VRChat 显示名称
        :param bind_type: 绑定类型 (manual/auto)
        :return: 绑定是否成功
        """
        pass

    @abstractmethod
    def unbind_user(self, qq_id: int) -> bool:
        """
        解除指定 QQ 号的绑定关系
        :param qq_id: 要解绑的 QQ 号
        :return: 解绑是否成功
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
    def get_vrc_id_by_qq(self, qq_id: int) -> Optional[str]:
        """
        通过 QQ 号查询绑定的 VRChat ID
        :param qq_id: 用户的 QQ 号
        :return: 绑定的 VRChat ID，若未绑定则返回 None
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
    def get_bindings_by_qq_list(self, qq_ids: List[int]) -> List[Dict]:
        """
        根据QQ列表查询绑定记录
        :param qq_ids: QQ号列表
        :return: 包含绑定信息的字典列表
        """
        pass

    @abstractmethod
    def get_all_bindings(self) -> List[Dict]:
        """
        获取数据库中所有的绑定记录列表
        :return: 包含所有绑定信息的字典列表
        """
        pass
