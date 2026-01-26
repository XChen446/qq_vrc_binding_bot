import pymysql
import logging
from typing import Optional, List, Dict
from .base import BaseDatabase

logger = logging.getLogger("Database.MySQL")

class MySQLDatabase(BaseDatabase):
    """MySQL 数据库后端实现"""
    def __init__(self, config: dict):
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 3306)
        self.user = config.get("user", "root")
        self.password = config.get("password", "")
        self.database = config.get("database", "bot_db")
        self.charset = "utf8mb4"
        
        # 初始化连接
        self._connect()
        self._create_tables()

    def _connect(self):
        """建立数据库连接"""
        try:
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            logger.info(f"已连接到 MySQL 数据库: {self.database}")
        except Exception as e:
            logger.error(f"连接 MySQL 数据库失败: {e}")
            raise

    def _ensure_connection(self):
        """确保连接可用，如果断开则重连"""
        try:
            self.conn.ping(reconnect=True)
        except Exception as e:
            logger.error(f"重连 MySQL 失败: {e}")
            self._connect()

    def _create_tables(self):
        """初始化数据库表结构"""
        self._ensure_connection()
        with self.conn.cursor() as cursor:
            # 1. 全局绑定表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS global_bindings (
                    qq_id BIGINT PRIMARY KEY COMMENT 'QQ号',
                    vrc_user_id VARCHAR(255) NOT NULL COMMENT 'VRChat User ID',
                    vrc_display_name VARCHAR(255) NOT NULL COMMENT 'VRChat 显示名称',
                    bind_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '绑定时间',
                    bind_type VARCHAR(50) DEFAULT 'manual' COMMENT '绑定类型',
                    origin_group_id BIGINT COMMENT '来源群组ID',
                    UNIQUE KEY idx_vrc_id (vrc_user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='全局绑定表';
            """)

            # 2. 验证表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS verifications (
                    qq_id BIGINT PRIMARY KEY COMMENT 'QQ号',
                    vrc_user_id VARCHAR(255) NOT NULL COMMENT 'VRChat User ID',
                    vrc_display_name VARCHAR(255) NOT NULL COMMENT 'VRChat 显示名称',
                    code VARCHAR(20) NOT NULL COMMENT '验证码',
                    group_id BIGINT COMMENT '来源群号',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='验证记录表';
            """)
            
            # 注意：群组绑定表 (group_{id}_bindings) 是动态创建的，此处不预先创建

    def _ensure_group_table(self, group_id: int):
        """动态创建群组绑定表"""
        self._ensure_connection()
        table_name = f"group_{group_id}_bindings"
        with self.conn.cursor() as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    qq_id BIGINT PRIMARY KEY COMMENT 'QQ号',
                    vrc_user_id VARCHAR(255) NOT NULL COMMENT 'VRChat User ID',
                    vrc_display_name VARCHAR(255) NOT NULL COMMENT 'VRChat 显示名称',
                    bind_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '绑定时间',
                    INDEX idx_vrc_id (vrc_user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='群组 {group_id} 绑定表';
            """)

    def bind_user(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, bind_type: str = "manual", group_id: Optional[int] = None) -> bool:
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                # 1. 更新全局表
                cursor.execute(
                    """
                    INSERT INTO global_bindings (qq_id, vrc_user_id, vrc_display_name, bind_type, origin_group_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        vrc_user_id = VALUES(vrc_user_id),
                        vrc_display_name = VALUES(vrc_display_name),
                        bind_type = VALUES(bind_type),
                        origin_group_id = IF(origin_group_id IS NULL, VALUES(origin_group_id), origin_group_id)
                    """,
                    (qq_id, vrc_user_id, vrc_display_name, bind_type, group_id)
                )

                # 2. 如果指定了群组，更新该群的绑定表
                if group_id:
                    self._ensure_group_table(group_id)
                    table_name = f"group_{group_id}_bindings"
                    cursor.execute(
                        f"""
                        INSERT INTO {table_name} (qq_id, vrc_user_id, vrc_display_name)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            vrc_user_id = VALUES(vrc_user_id),
                            vrc_display_name = VALUES(vrc_display_name)
                        """,
                        (qq_id, vrc_user_id, vrc_display_name)
                    )
            return True
        except Exception as e:
            logger.error(f"MySQL 绑定操作失败: {e}")
            return False

    def unbind_user_from_group(self, group_id: int, qq_id: int) -> bool:
        self._ensure_connection()
        try:
            # 1. 从特定群组表中删除
            self._ensure_group_table(group_id)
            table_name = f"group_{group_id}_bindings"
            with self.conn.cursor() as cursor:
                cursor.execute(f"DELETE FROM {table_name} WHERE qq_id = %s", (qq_id,))
                
                # 2. 更新全局表来源 (如果来源是该群，则置空)
                cursor.execute(
                    "UPDATE global_bindings SET origin_group_id = NULL WHERE qq_id = %s AND origin_group_id = %s",
                    (qq_id, group_id)
                )
            return True
        except Exception as e:
            logger.error(f"MySQL 群组解绑操作失败: {e}")
            return False

    def unbind_user_globally(self, qq_id: int) -> bool:
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                # 1. 查找所有可能包含该用户的群组表
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name LIKE 'group_%_bindings'
                """)
                tables = cursor.fetchall()
                
                # 2. 从每个群组表中删除该用户
                for table_info in tables:
                    table_name = table_info['TABLE_NAME']
                    # 注意：表名来自系统查询，相对安全，但最好还是小心
                    cursor.execute(f"DELETE FROM {table_name} WHERE qq_id = %s", (qq_id,))
                
                # 3. 删除全局绑定
                cursor.execute("DELETE FROM global_bindings WHERE qq_id = %s", (qq_id,))
            return True
        except Exception as e:
            logger.error(f"MySQL 全局解绑操作失败: {e}")
            return False

    def get_group_bindings(self, group_id: int) -> List[Dict]:
        """获取指定群的绑定记录"""
        self._ensure_connection()
        try:
            self._ensure_group_table(group_id)
            table_name = f"group_{group_id}_bindings"
            with self.conn.cursor() as cursor:
                cursor.execute(f"SELECT qq_id, vrc_user_id, vrc_display_name, bind_time FROM {table_name}")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"MySQL 获取群绑定记录失败: {e}")
            return []

    def get_qq_by_vrc_id(self, vrc_user_id: str) -> Optional[int]:
        self._ensure_connection()
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT qq_id FROM global_bindings WHERE vrc_user_id = %s", (vrc_user_id,))
            row = cursor.fetchone()
            return row['qq_id'] if row else None

    def get_binding(self, qq_id: int) -> Optional[Dict]:
        self._ensure_connection()
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type, origin_group_id FROM global_bindings WHERE qq_id = %s",
                (qq_id,)
            )
            return cursor.fetchone()

    def get_all_bindings(self) -> List[Dict]:
        self._ensure_connection()
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type, origin_group_id FROM global_bindings")
            return cursor.fetchall()

    def search_global_bindings(self, query: str) -> List[Dict]:
        """全局搜索绑定记录"""
        self._ensure_connection()
        with self.conn.cursor() as cursor:
            search_pattern = f"%{query}%"
            # 尝试将 query 转为 int 以匹配 qq_id
            qq_id_query = -1
            if query.isdigit():
                qq_id_query = int(query)

            sql = """
                SELECT qq_id, vrc_user_id, vrc_display_name, bind_time, bind_type, origin_group_id 
                FROM global_bindings 
                WHERE vrc_display_name LIKE %s 
                OR vrc_user_id LIKE %s 
                OR qq_id = %s
            """
            cursor.execute(sql, (search_pattern, search_pattern, qq_id_query))
            return cursor.fetchall()

    def add_verification(self, qq_id: int, vrc_user_id: str, vrc_display_name: str, code: str) -> bool:
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO verifications (qq_id, vrc_user_id, vrc_display_name, code)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        vrc_user_id = VALUES(vrc_user_id),
                        vrc_display_name = VALUES(vrc_display_name),
                        code = VALUES(code),
                        created_at = CURRENT_TIMESTAMP
                    """,
                    (qq_id, vrc_user_id, vrc_display_name, code)
                )
            return True
        except Exception as e:
            logger.error(f"MySQL 添加验证记录失败: {e}")
            return False

    def get_verification(self, qq_id: int) -> Optional[Dict]:
        self._ensure_connection()
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT qq_id, vrc_user_id, vrc_display_name, code, created_at FROM verifications WHERE qq_id = %s",
                (qq_id,)
            )
            return cursor.fetchone()

    def delete_verification(self, qq_id: int) -> bool:
        self._ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("DELETE FROM verifications WHERE qq_id = %s", (qq_id,))
            return True
        except Exception as e:
            logger.error(f"MySQL 删除验证记录失败: {e}")
            return False
