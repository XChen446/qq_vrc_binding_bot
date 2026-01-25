import sqlite3
import os
from typing import Optional, List, Dict
from .base import BaseDatabase

class SQLiteDatabase(BaseDatabase):
    """SQLite 数据库后端实现"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        # 确保数据库文件所在的目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # 建立连接，check_same_thread=False 允许在多线程（如异步 IO）中使用同一个连接
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        # 为 vrc_user_id 增加 UNIQUE 约束
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bindings (
                qq_id INTEGER PRIMARY KEY,
                vrc_user_id TEXT NOT NULL UNIQUE,
                vrc_display_name TEXT NOT NULL,
                bind_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bind_type TEXT DEFAULT 'manual'
            )
        ''')
        
        # 检查是否需要添加 bind_type 列 (用于升级旧表)
        cursor.execute("PRAGMA table_info(bindings)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'bind_type' not in columns:
            cursor.execute("ALTER TABLE bindings ADD COLUMN bind_type TEXT DEFAULT 'manual'")
            
        self.conn.commit()

    def bind_user(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, bind_type: str = "manual") -> bool:
        """执行绑定操作：插入或替换记录"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO bindings (qq_id, vrc_user_id, vrc_display_name, bind_type) VALUES (?, ?, ?, ?)",
                (qq_id, vrc_user_id, vrc_display_name, bind_type)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 绑定操作失败: {e}")
            return False

    def unbind_user(self, qq_id: int) -> bool:
        """执行解绑操作：删除记录"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM bindings WHERE qq_id = ?", (qq_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 解绑操作失败: {e}")
            return False

    def get_qq_by_vrc_id(self, vrc_user_id: str) -> Optional[int]:
        """根据 VRChat ID 查询绑定的 QQ 号"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT qq_id FROM bindings WHERE vrc_user_id = ?", (vrc_user_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_vrc_id_by_qq(self, qq_id: int) -> Optional[str]:
        """根据 QQ 号查询绑定的 VRChat ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT vrc_user_id FROM bindings WHERE qq_id = ?", (qq_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_binding(self, qq_id: int) -> Optional[Dict]:
        """根据 QQ 号查询完整的绑定记录"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type FROM bindings WHERE qq_id = ?", (qq_id,))
        row = cursor.fetchone()
        if row:
            return {
                "qq_id": row[0],
                "vrc_user_id": row[1],
                "vrc_display_name": row[2],
                "bind_time": row[3],
                "bind_type": row[4]
            }
        return None

    def get_all_bindings(self) -> List[Dict]:
        """查询所有绑定记录"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type FROM bindings")
        rows = cursor.fetchall()
        return [{
            "qq_id": r[0],
            "vrc_user_id": r[1],
            "vrc_display_name": r[2],
            "bind_time": r[3],
            "bind_type": r[4]
        } for r in rows]

    def get_bindings_by_qq_list(self, qq_ids: List[int]) -> List[Dict]:
        """根据QQ列表查询绑定记录"""
        if not qq_ids:
            return []
        placeholders = ','.join('?' * len(qq_ids))
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type FROM bindings WHERE qq_id IN ({placeholders})", qq_ids)
        rows = cursor.fetchall()
        return [{
            "qq_id": r[0],
            "vrc_user_id": r[1],
            "vrc_display_name": r[2],
            "bind_time": r[3],
            "bind_type": r[4]
        } for r in rows]
