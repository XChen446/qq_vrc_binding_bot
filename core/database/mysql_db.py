import pymysql
import logging
from typing import Optional, List, Dict
from .base import BaseDatabase

class MySQLDatabase(BaseDatabase):
    """MySQL 数据库后端实现，支持自动重连"""
    def __init__(self, config: Dict):
        self.host = config.get("host", "localhost")
        self.port = int(config.get("port", 3306))
        self.user = config.get("user", "root")
        self.password = config.get("password", "")
        self.database = config.get("database", "bot_db")
        
        self.conn = None
        self.logger = logging.getLogger("MySQL")
        self._connect()
        self._create_table()

    def _connect(self):
        """建立 MySQL 连接"""
        try:
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.logger.info("已成功连接到 MySQL 数据库")
        except Exception as e:
            self.logger.error(f"MySQL 数据库连接失败: {e}")
            raise

    def _ensure_connection(self):
        """确保连接有效，如果断开则尝试自动重连"""
        if not self.conn or not self.conn.open:
            self.logger.warning("MySQL 连接已断开，正在尝试重连...")
            self._connect()
        else:
            try:
                # 通过 ping 检查连接状态
                self.conn.ping(reconnect=True)
            except Exception:
                self._connect()

    def _create_table(self):
        """初始化绑定关系表结构"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                # 为 vrc_user_id 增加 UNIQUE 约束，确保一个 VRC 账号只能被一个 QQ 绑定
                sql = '''
                    CREATE TABLE IF NOT EXISTS bindings (
                        qq_id BIGINT PRIMARY KEY,
                        vrc_user_id VARCHAR(255) NOT NULL UNIQUE,
                        vrc_display_name VARCHAR(255) NOT NULL,
                        bind_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        bind_type VARCHAR(50) DEFAULT 'manual'
                    )
                '''
                cursor.execute(sql)
                
                # 检查是否需要添加 bind_type 列
                cursor.execute("SHOW COLUMNS FROM bindings LIKE 'bind_type'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE bindings ADD COLUMN bind_type VARCHAR(50) DEFAULT 'manual'")
                    
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"MySQL 初始化表失败: {e}")

    def bind_user(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, bind_type: str = "manual") -> bool:
        """执行绑定操作：插入或更新记录"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                sql = "REPLACE INTO bindings (qq_id, vrc_user_id, vrc_display_name, bind_type) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (qq_id, vrc_user_id, vrc_display_name, bind_type))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"MySQL 绑定用户失败: {e}")
            return False

    def unbind_user(self, qq_id: int) -> bool:
        """执行解绑操作：删除对应 QQ 的绑定记录"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                sql = "DELETE FROM bindings WHERE qq_id = %s"
                cursor.execute(sql, (qq_id,))
                affected = cursor.rowcount
            self.conn.commit()
            return affected > 0
        except Exception as e:
            self.logger.error(f"MySQL 解绑用户失败: {e}")
            return False

    def get_qq_by_vrc_id(self, vrc_user_id: str) -> Optional[int]:
        """根据 VRChat ID 查询对应的 QQ 号"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                sql = "SELECT qq_id FROM bindings WHERE vrc_user_id = %s"
                cursor.execute(sql, (vrc_user_id,))
                result = cursor.fetchone()
                if result:
                    return result['qq_id']
        except Exception as e:
            self.logger.error(f"MySQL 查询 QQ 失败: {e}")
        return None

    def get_vrc_id_by_qq(self, qq_id: int) -> Optional[str]:
        """根据 QQ 号查询对应的 VRChat ID"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                sql = "SELECT vrc_user_id FROM bindings WHERE qq_id = %s"
                cursor.execute(sql, (qq_id,))
                result = cursor.fetchone()
                if result:
                    return result['vrc_user_id']
        except Exception as e:
            self.logger.error(f"MySQL 查询 VRC ID 失败: {e}")
        return None

    def get_binding(self, qq_id: int) -> Optional[Dict]:
        """根据 QQ 号查询完整的绑定记录"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                sql = "SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type FROM bindings WHERE qq_id = %s"
                cursor.execute(sql, (qq_id,))
                result = cursor.fetchone()
                if result:
                    return {
                        "qq_id": result['qq_id'],
                        "vrc_user_id": result['vrc_user_id'],
                        "vrc_display_name": result['vrc_display_name'],
                        "bind_time": result.get('bind_time'),
                        "bind_type": result.get('bind_type', 'manual')
                    }
        except Exception as e:
            self.logger.error(f"MySQL 查询绑定记录失败: {e}")
        return None

    def get_all_bindings(self) -> List[Dict]:
        """获取所有绑定关系列表"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                sql = "SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type FROM bindings"
                cursor.execute(sql)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"MySQL 获取所有绑定记录失败: {e}")
            return []

    def get_bindings_by_qq_list(self, qq_ids: List[int]) -> List[Dict]:
        """根据QQ列表查询绑定记录"""
        if not qq_ids:
            return []
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                placeholders = ','.join(['%s'] * len(qq_ids))
                sql = f"SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type FROM bindings WHERE qq_id IN ({placeholders})"
                cursor.execute(sql, qq_ids)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"MySQL 根据QQ列表查询绑定记录失败: {e}")
            return []
