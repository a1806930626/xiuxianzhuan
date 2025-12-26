# data/migration.py

import aiosqlite
import json
from typing import Dict, Callable, Awaitable
from astrbot.api import logger
from ..core.config_manager import ConfigManager

LATEST_DB_VERSION = 1  # 初始版本号

MIGRATION_TASKS: Dict[int, Callable[[aiosqlite.Connection, ConfigManager], Awaitable[None]]] = {}

def migration(version: int):
    """注册数据库迁移任务的装饰器"""

    def decorator(func: Callable[[aiosqlite.Connection, ConfigManager], Awaitable[None]]):
        MIGRATION_TASKS[version] = func
        return func
    return decorator


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self, conn: aiosqlite.Connection, config_manager: ConfigManager):
        self.conn = conn
        self.config_manager = config_manager

    async def migrate(self):
        await self.conn.execute("PRAGMA foreign_keys = ON")
        
        # 检查是否存在数据库版本表
        async with self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_info'") as cursor:
            if await cursor.fetchone() is None:
                logger.info("未检测到数据库版本，将进行全新安装...")
                await self.conn.execute("BEGIN")
                # 使用最新的建表函数
                await _create_all_tables_v1(self.conn)
                await self.conn.execute("INSERT INTO db_info (version) VALUES (?)", (LATEST_DB_VERSION,))
                await self.conn.commit()
                logger.info(f"数据库已初始化到最新版本: v{LATEST_DB_VERSION}")
                return

        # 获取当前数据库版本
        async with self.conn.execute("SELECT version FROM db_info") as cursor:
            row = await cursor.fetchone()
            current_version = row[0] if row else 0

        logger.info(f"当前数据库版本: v{current_version}, 最新版本: v{LATEST_DB_VERSION}")
        
        # 执行迁移
        if current_version < LATEST_DB_VERSION:
            logger.info("检测到数据库需要升级...")
            for version in sorted(MIGRATION_TASKS.keys()):
                if current_version < version:
                    logger.info(f"正在执行数据库升级: v{current_version} -> v{version} ...")
                    try:
                        await self.conn.execute("BEGIN")
                        await MIGRATION_TASKS[version](self.conn, self.config_manager)
                        await self.conn.execute("UPDATE db_info SET version = ?", (version,))
                        await self.conn.commit()

                        logger.info(f"v{current_version} -> v{version} 升级成功！")
                        current_version = version
                    except Exception as e:
                        await self.conn.rollback()
                        logger.error(f"数据库 v{current_version} -> v{version} 升级失败，已回滚: {e}", exc_info=True)
                        raise
            logger.info("数据库升级完成！")
        else:
            logger.info("数据库结构已是最新。")


async def _create_all_tables_v1(conn: aiosqlite.Connection):
    """创建所有表结构（版本1）"""
    # 创建数据库版本表
    await conn.execute("CREATE TABLE IF NOT EXISTS db_info (version INTEGER NOT NULL)")
    
    # 创建玩家表
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS players (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        level_index INTEGER NOT NULL,
        experience INTEGER NOT NULL,
        spiritual_root TEXT NOT NULL,
        max_hp INTEGER NOT NULL,
        current_hp INTEGER NOT NULL,
        attack INTEGER NOT NULL,
        defense INTEGER NOT NULL,
        spirit INTEGER NOT NULL,
        gold INTEGER NOT NULL,
        last_sign_in TEXT NOT NULL,
        create_time TEXT NOT NULL,
        update_time TEXT NOT NULL,
        sect_id TEXT,
        sect_position TEXT NOT NULL,
        gongfa_id TEXT,
        equipment_ids TEXT NOT NULL
    )
    """)
    
    # 创建背包表
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id TEXT NOT NULL,
        item_id TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        PRIMARY KEY (user_id, item_id)
    )
    """)
    
    # 创建战斗日志表
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS combat_logs (
        log_id TEXT PRIMARY KEY,
        attacker_id TEXT NOT NULL,
        defender_id TEXT NOT NULL,
        result TEXT NOT NULL,
        damage INTEGER NOT NULL,
        experience_gained INTEGER NOT NULL,
        gold_gained INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        drop_items TEXT NOT NULL
    )
    """)


# 示例：如何添加新版本迁移
# @migration(2)
# async def _upgrade_v1_to_v2(conn: aiosqlite.Connection, config_manager: ConfigManager):
#     logger.info("开始执行 v1 -> v2 数据库迁移...")
#     # 在这里添加版本2的迁移逻辑
#     # 例如：添加新字段
#     # await conn.execute("ALTER TABLE players ADD COLUMN new_field INTEGER NOT NULL DEFAULT 0")
#     logger.info("v1 -> v2 数据库迁移完成！")