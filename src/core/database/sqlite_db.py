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
        
        # 全局绑定表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_bindings (
                qq_id INTEGER PRIMARY KEY,
                vrc_user_id TEXT NOT NULL UNIQUE,
                vrc_display_name TEXT NOT NULL,
                bind_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bind_type TEXT DEFAULT 'manual',
                origin_group_id INTEGER
            )
        ''')
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bindings'")
        if cursor.fetchone():
            cursor.execute("SELECT count(*) FROM global_bindings")
            if cursor.fetchone()[0] == 0:
                print("正在迁移旧绑定数据到 global_bindings...")
                try:
                    cursor.execute("""
                        INSERT INTO global_bindings (qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type)
                        SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type FROM bindings
                    """)
                    cursor.execute("ALTER TABLE bindings RENAME TO bindings_backup")
                except Exception as e:
                    print(f"数据迁移失败: {e}")

        # 全局验证表（已验证用户，无法通过群管操作删除）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS global_verifications (
                qq_id INTEGER PRIMARY KEY,
                vrc_user_id TEXT NOT NULL,
                vrc_display_name TEXT NOT NULL,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_by TEXT DEFAULT 'system'
            )
        ''')
        
        # 验证表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verifications (
                qq_id INTEGER PRIMARY KEY,
                vrc_user_id TEXT NOT NULL,
                vrc_display_name TEXT NOT NULL,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_expired BOOLEAN DEFAULT 0
            )
        ''')
        
        # 添加 is_expired 列（如果表已存在但缺少该列）
        try:
            cursor.execute("ALTER TABLE verifications ADD COLUMN is_expired BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            # 列已存在，忽略错误
            pass
            
        # 群组配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_settings (
                group_id INTEGER,
                setting_name TEXT,
                setting_value TEXT,
                PRIMARY KEY (group_id, setting_name)
            )
        ''')
        
        self.conn.commit()

    def _ensure_group_table(self, group_id: int):
        """确保群组绑定表存在"""
        table_name = f"group_{group_id}_bindings"
        cursor = self.conn.cursor()
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                qq_id INTEGER PRIMARY KEY,
                vrc_user_id TEXT NOT NULL,
                vrc_display_name TEXT NOT NULL,
                bind_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def bind_user(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, bind_type: str = "manual", group_id: Optional[int] = None) -> bool:
        """执行绑定操作：同时更新全局表和群组表"""
        try:
            cursor = self.conn.cursor()
            
            # 1. 检查是否存在旧记录以保护 origin_group_id
            cursor.execute("SELECT origin_group_id FROM global_bindings WHERE qq_id = ?", (qq_id,))
            row = cursor.fetchone()
            
            final_origin_group_id = group_id
            if row:
                if row[0] is not None:
                    final_origin_group_id = row[0]

            # 2. 更新全局表
            cursor.execute(
                "INSERT OR REPLACE INTO global_bindings (qq_id, vrc_user_id, vrc_display_name, bind_type, origin_group_id) VALUES (?, ?, ?, ?, ?)",
                (qq_id, vrc_user_id, vrc_display_name, bind_type, final_origin_group_id)
            )
            
            # 3. 如果指定了群组，更新群组表
            if group_id:
                self._ensure_group_table(group_id)
                table_name = f"group_{group_id}_bindings"
                cursor.execute(
                    f"INSERT OR REPLACE INTO {table_name} (qq_id, vrc_user_id, vrc_display_name) VALUES (?, ?, ?)",
                    (qq_id, vrc_user_id, vrc_display_name)
                )
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 绑定操作失败: {e}")
            return False

    def unbind_user_from_group(self, group_id: int, qq_id: int) -> bool:
        """从指定群聊中移除绑定记录"""
        try:
            cursor = self.conn.cursor()
            # 1. 从群组表删除
            self._ensure_group_table(group_id)
            table_name = f"group_{group_id}_bindings"
            cursor.execute(f"DELETE FROM {table_name} WHERE qq_id = ?", (qq_id,))
            deleted_rows = cursor.rowcount
            
            # 2. 更新全局表来源 (如果来源是该群，则置空)
            cursor.execute(
                "UPDATE global_bindings SET origin_group_id = NULL WHERE qq_id = ? AND origin_group_id = ?",
                (qq_id, group_id)
            )
            
            self.conn.commit()
            return deleted_rows > 0
        except Exception as e:
            print(f"SQLite 群组解绑操作失败: {e}")
            return False

    def unbind_user_globally(self, qq_id: int) -> bool:
        """全局解绑"""
        try:
            cursor = self.conn.cursor()
            
            # 1. 获取所有以 group_ 开头的表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'group_%_bindings'")
            tables = cursor.fetchall()
            
            # 2. 从所有群组表中删除
            for (table_name,) in tables:
                cursor.execute(f"DELETE FROM {table_name} WHERE qq_id = ?", (qq_id,))
                
            # 3. 从全局表删除
            cursor.execute("DELETE FROM global_bindings WHERE qq_id = ?", (qq_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 全局解绑操作失败: {e}")
            return False

    def get_qq_by_vrc_id(self, vrc_user_id: str) -> Optional[int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT qq_id FROM global_bindings WHERE vrc_user_id = ?", (vrc_user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def get_binding(self, qq_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type, origin_group_id FROM global_bindings WHERE qq_id = ?", (qq_id,))
        row = cursor.fetchone()
        if row:
            return {
                "qq_id": row[0],
                "vrc_user_id": row[1],
                "vrc_display_name": row[2],
                "bind_time": row[3],
                "bind_type": row[4],
                "origin_group_id": row[5]
            }
        return None

    def get_all_bindings(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type, origin_group_id FROM global_bindings")
        rows = cursor.fetchall()
        return [{
            "qq_id": r[0],
            "vrc_user_id": r[1],
            "vrc_display_name": r[2],
            "bind_time": r[3],
            "bind_type": r[4],
            "origin_group_id": r[5]
        } for r in rows]

    def get_group_bindings(self, group_id: int) -> List[Dict]:
        """获取指定群的绑定记录"""
        try:
            self._ensure_group_table(group_id)
            table_name = f"group_{group_id}_bindings"
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT qq_id, vrc_user_id, vrc_display_name, bind_time FROM {table_name}")
            rows = cursor.fetchall()
            return [{
                "qq_id": r[0],
                "vrc_user_id": r[1],
                "vrc_display_name": r[2],
                "bind_time": r[3]
            } for r in rows]
        except Exception as e:
            print(f"获取群绑定记录失败: {e}")
            return []

    def get_group_member_binding(self, group_id: int, qq_id: int) -> Optional[Dict]:
        """获取指定群成员的绑定记录"""
        try:
            self._ensure_group_table(group_id)
            table_name = f"group_{group_id}_bindings"
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT qq_id, vrc_user_id, vrc_display_name, bind_time FROM {table_name} WHERE qq_id = ?", (qq_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "qq_id": row[0],
                    "vrc_user_id": row[1],
                    "vrc_display_name": row[2],
                    "bind_time": row[3]
                }
            return None
        except Exception as e:
            print(f"获取群成员绑定记录失败: {e}")
            return None

    def add_verification(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, code: str) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO verifications (qq_id, vrc_user_id, vrc_display_name, code, is_expired) VALUES (?, ?, ?, ?, ?)",
                (qq_id, vrc_user_id, vrc_display_name, code, 0)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 添加验证记录失败: {e}")
            return False

    def get_verification(self, qq_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT qq_id, vrc_user_id, vrc_display_name, code, created_at, is_expired, (strftime('%s','now') - strftime('%s', created_at)) as elapsed FROM verifications WHERE qq_id = ?", (qq_id,))
        row = cursor.fetchone()
        if row:
            return {
                "qq_id": row[0],
                "vrc_user_id": row[1],
                "vrc_display_name": row[2],
                "code": row[3],
                "created_at": row[4],
                "is_expired": bool(row[5]),
                "elapsed": int(row[6]) if row[6] is not None else 0
            }
        return None

    def delete_verification(self, qq_id: int) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM verifications WHERE qq_id = ?", (qq_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 删除验证记录失败: {e}")
            return False

    def mark_verification_expired(self, qq_id: int) -> bool:
        """标记验证码为已过期"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE verifications SET code = ?, is_expired = 1 WHERE qq_id = ?", 
                          ("Ciallo～(∠・ω< )⌒★", qq_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 标记验证记录过期失败: {e}")
            return False

    def expire_outdated_verifications(self, expiry_seconds: int) -> int:
        """批量标记过期的验证记录"""
        try:
            import time
            cutoff_time = time.time() - expiry_seconds
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE verifications SET code = ?, is_expired = 1 WHERE created_at < ? AND is_expired = 0",
                ("Ciallo～(∠・ω< )⌒★", str(cutoff_time))
            )
            self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"SQLite 批量标记过期记录失败: {e}")
            return 0

    def set_group_vrc_group_id(self, group_id: int, vrc_group_id: str) -> bool:
        """设置群组绑定的 VRChat 群组 ID"""
        try:
            self._ensure_connection()
            # 确保存储群组配置的表存在 (这里我们使用一个简单的 group_configs 表)
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_configs (
                    group_id INTEGER PRIMARY KEY,
                    vrc_group_id TEXT
                )
            ''')
            
            cursor.execute(
                "INSERT OR REPLACE INTO group_configs (group_id, vrc_group_id) VALUES (?, ?)",
                (group_id, vrc_group_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 设置群组 VRChat 群组 ID 失败: {e}")
            return False

    def get_group_vrc_group_id(self, group_id: int) -> Optional[str]:
        """获取群组绑定的 VRChat 群组 ID"""
        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='group_configs'")
            if not cursor.fetchone():
                return None
                
            cursor.execute("SELECT vrc_group_id FROM group_configs WHERE group_id = ?", (group_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"SQLite 获取群组 VRChat 群组 ID 失败: {e}")
            return None

    def delete_group_vrc_group_id(self, group_id: int) -> bool:
        """删除群组绑定的 VRChat 群组 ID"""
        try:
            self._ensure_connection()
            cursor = self.conn.cursor()
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='group_configs'")
            if not cursor.fetchone():
                return False
                
            cursor.execute("DELETE FROM group_configs WHERE group_id = ?", (group_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"SQLite 删除群组 VRChat 群组 ID 失败: {e}")
            return False

    def search_global_bindings(self, query: str) -> List[Dict]:
        """全局搜索绑定记录"""
        cursor = self.conn.cursor()
        search_pattern = f"%{query}%"
        qq_id_query = -1
        if query.isdigit():
            qq_id_query = int(query)

        sql = """
            SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type, origin_group_id 
            FROM global_bindings 
            WHERE vrc_display_name LIKE ? 
            OR vrc_user_id LIKE ? 
            OR qq_id = ?
        """
        cursor.execute(sql, (search_pattern, search_pattern, qq_id_query))
        rows = cursor.fetchall()
        return [{
            "qq_id": r[0],
            "vrc_user_id": r[1],
            "vrc_display_name": r[2],
            "bind_time": r[3],
            "bind_type": r[4],
            "origin_group_id": r[5]
        } for r in rows]

    def set_group_setting(self, group_id: int, setting_name: str, setting_value: str) -> bool:
        """设置群组特定配置"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO group_settings (group_id, setting_name, setting_value) VALUES (?, ?, ?)",
                (group_id, setting_name, setting_value)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 设置群组配置失败: {e}")
            return False

    def get_group_setting(self, group_id: int, setting_name: str) -> Optional[str]:
        """获取群组特定配置"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT setting_value FROM group_settings WHERE group_id = ? AND setting_name = ?",
                (group_id, setting_name)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"SQLite 获取群组配置失败: {e}")
            return None

    def add_global_verification(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, verified_by: str = "system") -> bool:
        """添加全局验证记录（用户已完成验证）"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO global_verifications (qq_id, vrc_user_id, vrc_display_name, verified_by) VALUES (?, ?, ?, ?)",
                (qq_id, vrc_user_id, vrc_display_name, verified_by)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"SQLite 添加全局验证记录失败: {e}")
            return False

    def get_global_verification(self, qq_id: int) -> Optional[Dict]:
        """获取全局验证记录"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT qq_id, vrc_user_id, vrc_display_name, verified_at, verified_by FROM global_verifications WHERE qq_id = ?",
                (qq_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "qq_id": row[0],
                    "vrc_user_id": row[1],
                    "vrc_display_name": row[2],
                    "verified_at": row[3],
                    "verified_by": row[4]
                }
            return None
        except Exception as e:
            print(f"SQLite 获取全局验证记录失败: {e}")
            return None

    def get_group_binding_with_global_fallback(self, group_id: int, qq_id: int) -> Optional[Dict]:
        """获取群组绑定记录，如果群组中没有则从全局验证获取"""
        # 首先尝试从群组表获取
        group_binding = self.get_group_member_binding(group_id, qq_id)
        if group_binding:
            return group_binding
        
        # 如果群组中没有，则尝试从全局验证表获取
        global_verification = self.get_global_verification(qq_id)
        if global_verification:
            return {
                "qq_id": global_verification["qq_id"],
                "vrc_user_id": global_verification["vrc_user_id"],
                "vrc_display_name": global_verification["vrc_display_name"],
                "bind_time": global_verification["verified_at"]
            }
        
        # 最后尝试从全局绑定表获取
        return self.get_binding(qq_id)

    def _ensure_connection(self):
        """确保数据库连接正常"""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)

    def search_bindings(self, query: str) -> List[Dict]:
        """搜索绑定记录（全局）"""
        return self.search_global_bindings(query)

    def get_pending_vrc_info(self, user_id: int) -> Optional[Dict]:
        """获取用户待处理的VRChat信息"""
        # 这个信息通常存储在内存中，而不是数据库中
        # 但我们可以从验证表中获取相关信息
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT vrc_user_id, vrc_display_name FROM verifications WHERE qq_id = ? AND is_expired = 0",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "vrc_user_id": row[0],
                    "vrc_display_name": row[1]
                }
            return None
        except Exception as e:
            print(f"SQLite 获取待处理VRChat信息失败: {e}")
            return None