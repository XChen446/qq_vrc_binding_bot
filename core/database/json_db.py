import json
import os
import datetime
from typing import Optional, List, Dict
from .base import BaseDatabase

class JSONDatabase(BaseDatabase):
    """基于 JSON 文件的数据库后端实现"""
    def __init__(self, file_path: str):
        self.file_path = file_path
        # 自动创建存储目录
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict:
        """从文件中加载数据"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save(self):
        """将数据保存到文件"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                # 使用缩进和 utf-8 编码保存
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"JSON 数据库保存失败: {e}")

    def bind_user(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, bind_type: str = "manual") -> bool:
        """执行绑定操作"""
        self.data[str(qq_id)] = {
            "vrc_user_id": vrc_user_id,
            "vrc_display_name": vrc_display_name,
            "bind_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bind_type": bind_type
        }
        self._save()
        return True

    def unbind_user(self, qq_id: int) -> bool:
        """执行解绑操作"""
        if str(qq_id) in self.data:
            del self.data[str(qq_id)]
            self._save()
            return True
        return False

    def get_qq_by_vrc_id(self, vrc_user_id: str) -> Optional[int]:
        """反查 QQ 号"""
        for qq_id, info in self.data.items():
            if info["vrc_user_id"] == vrc_user_id:
                return int(qq_id)
        return None

    def get_vrc_id_by_qq(self, qq_id: int) -> Optional[str]:
        """查询 VRC ID"""
        info = self.data.get(str(qq_id))
        return info["vrc_user_id"] if info else None

    def get_binding(self, qq_id: int) -> Optional[Dict]:
        """查询完整的绑定记录"""
        info = self.data.get(str(qq_id))
        if info:
            return {
                "qq_id": qq_id,
                "vrc_user_id": info["vrc_user_id"],
                "vrc_display_name": info["vrc_display_name"],
                "bind_time": info.get("bind_time"),
                "bind_type": info.get("bind_type", "manual")
            }
        return None

    def get_all_bindings(self) -> List[Dict]:
        """获取所有记录"""
        return [{
            "qq_id": int(k), 
            "vrc_user_id": v["vrc_user_id"], 
            "vrc_display_name": v["vrc_display_name"],
            "bind_time": v.get("bind_time"),
            "bind_type": v.get("bind_type", "manual")
        } for k, v in self.data.items()]

    def get_bindings_by_qq_list(self, qq_ids: List[int]) -> List[Dict]:
        """根据QQ列表查询绑定记录"""
        if not qq_ids:
            return []
        qq_set = set(qq_ids)
        return [{
            "qq_id": int(k), 
            "vrc_user_id": v["vrc_user_id"], 
            "vrc_display_name": v["vrc_display_name"],
            "bind_time": v.get("bind_time"),
            "bind_type": v.get("bind_type", "manual")
        } for k, v in self.data.items() if int(k) in qq_set]
