from .base import BaseDatabase
from .sqlite_db import SQLiteDatabase

def get_database(config: dict) -> BaseDatabase:
    db_config = config.get("database", {})
    db_type = db_config.get("type", "sqlite").lower()
    
    if db_type == "sqlite":
        db_path = db_config.get("path", "data/bot.db")
        return SQLiteDatabase(db_path)
    elif db_type == "mysql":
        try:
            from .mysql_db import MySQLDatabase
            return MySQLDatabase(db_config)
        except ImportError:
            print("Error: 'pymysql' module is not installed. Please install it using 'pip install pymysql'. Falling back to SQLite.")
            db_path = db_config.get("path", "data/bot.db")
            return SQLiteDatabase(db_path)
        except Exception as e:
            print(f"Error initializing MySQL database: {e}. Falling back to SQLite.")
            db_path = db_config.get("path", "data/bot.db")
            return SQLiteDatabase(db_path)
    else:
        # 默认为 sqlite，或者抛出不支持的错误
        if db_type in ["json"]:
            print(f"Warning: Database type '{db_type}' is no longer supported. Falling back to SQLite.")
            db_path = db_config.get("path", "data/bot.db")
            return SQLiteDatabase(db_path)
        raise ValueError(f"Unsupported database type: {db_type}")
