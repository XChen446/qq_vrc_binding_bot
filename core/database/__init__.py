from .base import BaseDatabase
from .sqlite_db import SQLiteDatabase
from .json_db import JSONDatabase
from .mysql_db import MySQLDatabase

def get_database(config: dict) -> BaseDatabase:
    db_config = config.get("database", {})
    db_type = db_config.get("type", "sqlite").lower()
    
    if db_type == "sqlite":
        db_path = db_config.get("path", "data/bot.db")
        return SQLiteDatabase(db_path)
    elif db_type == "json":
        db_path = db_config.get("path", "data/bot.db")
        return JSONDatabase(db_path)
    elif db_type == "mysql":
        return MySQLDatabase(db_config)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
