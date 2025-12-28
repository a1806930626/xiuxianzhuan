# data/migration.py

import aiosqlite
import json
from typing import Dict, Callable, Awaitable
from astrbot.api import logger
from ..core.config_manager import ConfigManager

LATEST_DB_VERSION = 9  # 最新版本号

MIGRATION_TASKS: Dict[int, Callable[[aiosqlite.Connection, ConfigManager], Awaitable[None]]] = {}

def migration(version: int):
    """注册数据库迁移任务的装饰器"""

    def decorator(func: Callable[[aiosqlite.Connection, ConfigManager], Awaitable[None]]):
        MIGRATION_TASKS[version] = func
        return func
    return decorator

def _calculate_upgrade_exp_by_realm(realm_name: str) -> int:
    """根据境界名称计算升级经验"""
    # 境界名称与经验值的映射
    realm_exp_map = {
        "练气一层": 0,
        "练气二层": 50,
        "练气三层": 100,
        "练气四层": 200,
        "练气五层": 350,
        "练气六层": 500,
        "练气七层": 700,
        "练气八层": 1000,
        "练气九层": 1400,
        "练气十层": 2000,
        "筑基初期": 3000,
        "筑基中期": 4500,
        "筑基后期": 6500,
        "金丹初期": 9000,
        "金丹中期": 12000,
        "金丹后期": 16000,
        "元婴初期": 21000,
        "元婴中期": 27000,
        "元婴后期": 35000,
        "化神初期": 45000,
        "化神中期": 57000,
        "化神后期": 72000,
        "炼虚初期": 90000,
        "炼虚中期": 110000,
        "炼虚后期": 135000,
        "合体初期": 165000,
        "合体中期": 200000,
        "合体后期": 240000,
        "大乘初期": 285000,
        "大乘中期": 335000,
        "大乘后期": 400000
    }
    
    # 如果找不到对应的境界，默认使用练气一层
    return realm_exp_map.get(realm_name, 0)


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
            spirit INTEGER NOT NULL,
            spiritual_root TEXT NOT NULL,
            max_hp INTEGER NOT NULL,
            current_hp INTEGER NOT NULL,
            attack INTEGER NOT NULL,
            defense INTEGER NOT NULL,
            speed INTEGER NOT NULL,
            spirit_stone INTEGER NOT NULL,
            last_sign_in TEXT NOT NULL,
            create_time TEXT NOT NULL,
            update_time TEXT NOT NULL,
            sect_id TEXT,
            sect_position TEXT NOT NULL,
            gongfa_ids TEXT NOT NULL,
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
            spirit_stone_gained INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            drop_items TEXT NOT NULL
        )
    """)
    
    # 创建物品表
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        item_type TEXT NOT NULL,
        category TEXT NOT NULL,
        quality TEXT NOT NULL,
        effect TEXT NOT NULL,
        price INTEGER NOT NULL,
        max_stack INTEGER NOT NULL,
        usage_requirements TEXT NOT NULL,
        upgrade_level INTEGER NOT NULL DEFAULT 0,
        base_attack INTEGER NOT NULL DEFAULT 0,
        base_defense INTEGER NOT NULL DEFAULT 0,
        base_speed INTEGER NOT NULL DEFAULT 0,
        base_hp INTEGER NOT NULL DEFAULT 0,
        base_spirit INTEGER NOT NULL DEFAULT 0
    )
    """)
    
    # 插入初始物品数据
    items_config = config_manager.items if hasattr(config_manager, 'items') else {}
    for item_id, item_data in items_config.items():
        # 根据物品类型确定分类
        category = "丹药" if item_data.get("type") == "consumable" else ""
        if item_data.get("type") == "equipment":
            category = "装备"
        elif item_data.get("type") == "gongfa":
            category = "功法"
        elif item_data.get("type") == "consumable":
            category = "丹药"
        
        await conn.execute("""
        INSERT OR REPLACE INTO items 
        (item_id, name, description, item_type, category, quality, effect, price, max_stack, usage_requirements) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            item_data.get("name", ""),
            item_data.get("description", ""),
            item_data.get("type", "consumable"),
            category,
            item_data.get("quality", "common"),
            str(item_data.get("effects", {})),
            item_data.get("price", 0),
            item_data.get("max_stack", 99),
            "[]"
        ))


@migration(2)
async def _upgrade_v1_to_v2(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v1 -> v2 数据库迁移...")
    # 添加speed列到players表
    await conn.execute("ALTER TABLE players ADD COLUMN speed INTEGER NOT NULL DEFAULT 0")
    logger.info("v1 -> v2 数据库迁移完成！")


@migration(3)
async def _upgrade_v2_to_v3(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v2 -> v3 数据库迁移...")
    
    # 首先创建gongfas表（如果不存在）
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS gongfas (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        upgrade_exp INTEGER NOT NULL DEFAULT 0,
        attack_bonus INTEGER NOT NULL DEFAULT 0,
        hp_bonus INTEGER NOT NULL DEFAULT 0,
        defense_bonus INTEGER NOT NULL DEFAULT 0,
        speed_bonus INTEGER NOT NULL DEFAULT 0,
        cultivation_speed_bonus REAL NOT NULL DEFAULT 0.0
    )
    """)
    
    # 将players表中的gongfa_id列改为gongfa_ids，支持存储多个功法
    # 由于SQLite不直接支持修改列名，我们需要创建新表并迁移数据
    await conn.execute("""
    ALTER TABLE players ADD COLUMN gongfa_ids TEXT NOT NULL DEFAULT '[]'
    """)
    
    # 从旧的gongfa_id字段迁移数据到新的gongfa_ids字段
    # 将单个功法ID转换为包含单个元素的JSON数组
    cursor = await conn.execute("SELECT user_id, gongfa_id FROM players WHERE gongfa_id IS NOT NULL")
    rows = await cursor.fetchall()
    
    for row in rows:
        user_id, old_gongfa_id = row
        if old_gongfa_id:  # 如果有旧的功法ID
            import json
            gongfa_list = json.dumps([old_gongfa_id])  # 将单个ID转换为JSON数组
            await conn.execute("UPDATE players SET gongfa_ids = ? WHERE user_id = ?", (gongfa_list, user_id))
    
    # 为了安全，删除旧的gongfa_id列
    # 注意：SQLite不支持直接删除列，我们保留它但不再使用
    
    # 添加《长春功》功法
    await conn.execute("""
    INSERT INTO gongfas (id, name, upgrade_exp, attack_bonus, hp_bonus, defense_bonus, speed_bonus, cultivation_speed_bonus)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("changchun_gong", "长春功", 1000, 0, 100, 0, 0, 0.05))
    
    logger.info("v2 -> v3 数据库迁移完成！")
#     # 在这里添加版本3的迁移逻辑
#     logger.info("v2 -> v3 数据库迁移完成！")


@migration(4)
async def _upgrade_v3_to_v4(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v3 -> v4 数据库迁移...")
    
    # 创建装备表
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS equipments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        slot TEXT NOT NULL,
        base_attack INTEGER NOT NULL DEFAULT 0,
        base_defense INTEGER NOT NULL DEFAULT 0,
        base_speed INTEGER NOT NULL DEFAULT 0,
        base_hp INTEGER NOT NULL DEFAULT 0,
        base_spirit INTEGER NOT NULL DEFAULT 0,
        upgrade_level INTEGER NOT NULL DEFAULT 0,
        quality TEXT NOT NULL,
        price INTEGER NOT NULL,
        required_realm INTEGER NOT NULL DEFAULT 0
    )
    """)
    
    # 添加初始装备数据
    await conn.execute("""
    INSERT INTO equipments (id, name, description, slot, base_attack, base_defense, base_speed, base_hp, base_spirit, quality, price)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("beginner_sword", "新手剑", "基础的修仙者武器", "weapon", 10, 0, 0, 0, 0, "黄", 100))
    
    await conn.execute("""
    INSERT INTO equipments (id, name, description, slot, base_attack, base_defense, base_speed, base_hp, base_spirit, quality, price)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("beginner_robe", "新手袍", "基础的修仙者护甲", "armor", 0, 10, 0, 0, 0, "黄", 100))
    
    await conn.execute("""
    INSERT INTO equipments (id, name, description, slot, base_attack, base_defense, base_speed, base_hp, base_spirit, quality, price)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("beginner_boots", "新手靴", "基础的修仙者鞋子", "shoes", 0, 0, 10, 0, 0, "黄", 100))
    
    await conn.execute("""
    INSERT INTO equipments (id, name, description, slot, base_attack, base_defense, base_speed, base_hp, base_spirit, quality, price)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("beginner_amulet", "新手护符", "基础的修仙者饰品", "accessory1", 0, 0, 0, 0, 1, "黄", 100))
    
    logger.info("v3 -> v4 数据库迁移完成！")


@migration(5)
async def _upgrade_v4_to_v5(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v4 -> v5 数据库迁移...")
    
    # 添加category列（如果不存在）
    try:
        await conn.execute("ALTER TABLE items ADD COLUMN category TEXT NOT NULL DEFAULT ''")
    except:
        # 如果列已存在，忽略错误
        pass
    
    # 更新现有物品的分类
    items_config = config_manager.items if hasattr(config_manager, 'items') else {}
    for item_id, item_data in items_config.items():
        # 根据物品类型确定分类
        category = "丹药" if item_data.get("type") == "consumable" else ""
        if item_data.get("type") == "equipment":
            category = "装备"
        elif item_data.get("type") == "gongfa":
            category = "功法"
        elif item_data.get("type") == "consumable":
            category = "丹药"
        
        await conn.execute("""
        UPDATE items 
        SET category = ? 
        WHERE item_id = ?
        """, (
            category,
            item_id
        ))
    
    logger.info("v4 -> v5 数据库迁移完成！")


@migration(6)
async def _upgrade_v5_to_v6(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v5 -> v6 数据库迁移...")
    
    # 从items配置中添加功法到gongfas表
    items_config = config_manager.items if hasattr(config_manager, 'items') else {}
    for item_id, item_data in items_config.items():
        # 只处理功法类型的物品
        if item_data.get("type") == "gongfa":
            # 检查功法是否已存在于gongfas表中
            cursor = await conn.execute("SELECT id FROM gongfas WHERE id = ?", (item_id,))
            existing = await cursor.fetchone()
            
            if not existing:
                # 如果不存在，则插入新的功法
                await conn.execute("""
                INSERT INTO gongfas 
                (id, name, upgrade_exp, attack_bonus, hp_bonus, defense_bonus, speed_bonus, cultivation_speed_bonus)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id,
                    item_data.get("name", ""),
                    self._calculate_upgrade_exp_by_realm(item_data.get("required_realm", "练气一层")),  # 用required_realm计算升级经验
                    item_data.get("attack_bonus", 0),
                    item_data.get("hp_bonus", 0),
                    item_data.get("defense_bonus", 0),
                    item_data.get("speed_bonus", 0),
                    item_data.get("cultivation_speed_bonus", 0.0)
                ))
    
    logger.info("v5 -> v6 数据库迁移完成！")


@migration(7)
async def _upgrade_v6_to_v7(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v6 -> v7 数据库迁移...")
    
    # 创建丹药表
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS danyao (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        effect TEXT NOT NULL
    )
    """)
    
    # 从items配置中迁移丹药数据到danyao表
    items_config = config_manager.items if hasattr(config_manager, 'items') else {}
    for item_id, item_data in items_config.items():
        # 只处理丹药类型的物品
        if item_data.get("type") == "consumable":
            # 检查丹药是否已存在于danyao表中
            cursor = await conn.execute("SELECT id FROM danyao WHERE id = ?", (item_id,))
            existing = await cursor.fetchone()
            
            if not existing:
                # 如果不存在，则插入新的丹药
                import json
                effects = item_data.get("effects", {})
                await conn.execute("""
                INSERT INTO danyao 
                (id, name, effect)
                VALUES (?, ?, ?)
                """, (
                    item_id,
                    item_data.get("name", ""),
                    json.dumps(effects)  # 将效果存储为JSON字符串
                ))
    
    logger.info("v6 -> v7 数据库迁移完成！")


@migration(8)
async def _upgrade_v7_to_v8(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v7 -> v8 数据库迁移...")
    
    # 更新items表，为consumable类型的物品清理effect字段
    # 从items表中获取所有consumable类型的物品
    async with conn.execute("SELECT item_id, name FROM items WHERE item_type = 'consumable'") as cursor:
        rows = await cursor.fetchall()
        
        for row in rows:
            item_id, name = row
            # 检查这个consumable是否在danyao表中有对应的记录
            cursor2 = await conn.execute("SELECT effect FROM danyao WHERE id = ?", (item_id,))
            danyao_row = await cursor2.fetchone()
            
            if danyao_row:
                # 如果在danyao表中存在，则将items表中的effect字段设置为空字符串
                # 这样可以确保effect只存储在danyao表中
                await conn.execute(
                    "UPDATE items SET effect = ? WHERE item_id = ?", 
                    ("", item_id)
                )
    
    await conn.commit()
    logger.info("v7 -> v8 数据库迁移完成！")


@migration(9)
async def _upgrade_v8_to_v9(conn: aiosqlite.Connection, config_manager: ConfigManager):
    logger.info("开始执行 v8 -> v9 数据库迁移...")
    
    # 创建宗门表
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS sects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        leader_id TEXT,
        level INTEGER NOT NULL DEFAULT 1,
        experience INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 从配置文件迁移宗门数据
    sects_config = config_manager.sects if hasattr(config_manager, 'sects') else {}
    for sect_id, sect_data in sects_config.items():
        # 检查宗门是否已存在
        cursor = await conn.execute("SELECT id FROM sects WHERE id = ?", (sect_id,))
        existing = await cursor.fetchone()
        
        if not existing:
            # 如果不存在，则插入新的宗门
            # 使用system作为默认宗主ID，因为实际宗主是在玩家加入时设置的
            await conn.execute("""
            INSERT INTO sects (id, name, leader_id, level)
            VALUES (?, ?, ?, ?)
            """, (
                sect_id,
                sect_data.get("name", ""),
                None,  # 实际宗主ID将在玩家创建宗门时设置
                1  # 默认等级为1
            ))
    
    logger.info("v8 -> v9 数据库迁移完成！")