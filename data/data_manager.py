import aiosqlite
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models import Player, Item, InventoryItem, CombatLog
from .migration import MigrationManager


class DataBase:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)
        self.db_path = self.plugin_dir / "xiuxianzhuan_data.db"
        self.conn: Optional[aiosqlite.Connection] = None
    
    async def init(self):
        """初始化数据库连接和表结构"""
        # 确保数据目录存在
        self.db_path.parent.mkdir(exist_ok=True)
        
        # 连接数据库
        self.conn = await aiosqlite.connect(self.db_path)
        
        # 执行数据库迁移
        from ..core.config_manager import ConfigManager
        config_manager = ConfigManager(self.plugin_dir.parent)
        migration_manager = MigrationManager(self.conn, config_manager)
        await migration_manager.migrate()
        
        await self.conn.execute("PRAGMA foreign_keys = ON")
    
    async def close(self):
        """关闭数据库连接"""
        if self.conn:
            await self.conn.close()
            self.conn = None
    
    # 注意：表创建逻辑已移至migration.py中的_create_all_tables_v1函数
    # 现在由MigrationManager负责处理表结构的创建和更新
    
    # 玩家相关操作
    async def get_player_by_id(self, user_id: str) -> Optional[Player]:
        """根据用户ID获取玩家信息"""
        async with self.conn.execute(
            "SELECT * FROM players WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                import json
                return Player(
                    user_id=row[0],
                    name=row[1],
                    level_index=row[2],
                    experience=row[3],
                    spiritual_root=row[4],
                    max_hp=row[5],
                    current_hp=row[6],
                    attack=row[7],
                    defense=row[8],
                    spirit=row[9],
                    gold=row[10],
                    last_sign_in=row[11],
                    create_time=row[12],
                    update_time=row[13],
                    sect_id=row[14],
                    sect_position=row[15],
                    gongfa_id=row[16],
                    equipment_ids=json.loads(row[17])
                )
            return None
    
    async def create_player(self, player: Player) -> bool:
        """创建新玩家"""
        try:
            import json
            await self.conn.execute(
                """
                INSERT INTO players (
                    user_id, name, level_index, experience, spiritual_root, 
                    max_hp, current_hp, attack, defense, spirit, gold, 
                    last_sign_in, create_time, update_time, sect_id, 
                    sect_position, gongfa_id, equipment_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player.user_id, player.name, player.level_index, player.experience,
                    player.spiritual_root, player.max_hp, player.current_hp, player.attack,
                    player.defense, player.spirit, player.gold, player.last_sign_in,
                    player.create_time, player.update_time, player.sect_id,
                    player.sect_position, player.gongfa_id, json.dumps(player.equipment_ids)
                )
            )
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"创建玩家失败: {e}")
            return False
    
    async def update_player(self, player: Player) -> bool:
        """更新玩家信息"""
        try:
            import json
            await self.conn.execute(
                """
                UPDATE players SET 
                    name = ?, level_index = ?, experience = ?, spiritual_root = ?, 
                    max_hp = ?, current_hp = ?, attack = ?, defense = ?, spirit = ?, 
                    gold = ?, last_sign_in = ?, update_time = ?, sect_id = ?, 
                    sect_position = ?, gongfa_id = ?, equipment_ids = ?
                WHERE user_id = ?
                """,
                (
                    player.name, player.level_index, player.experience, player.spiritual_root,
                    player.max_hp, player.current_hp, player.attack, player.defense,
                    player.spirit, player.gold, player.last_sign_in, player.update_time,
                    player.sect_id, player.sect_position, player.gongfa_id,
                    json.dumps(player.equipment_ids), player.user_id
                )
            )
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"更新玩家失败: {e}")
            return False
    
    # 背包相关操作
    async def get_player_inventory(self, user_id: str) -> List[InventoryItem]:
        """获取玩家背包"""
        async with self.conn.execute(
            "SELECT user_id, item_id, quantity FROM inventory WHERE user_id = ?", (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                InventoryItem(user_id=row[0], item_id=row[1], quantity=row[2])
                for row in rows
            ]
    
    async def add_item_to_inventory(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
        """添加物品到背包"""
        try:
            # 检查是否已存在该物品
            async with self.conn.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    # 更新数量
                    await self.conn.execute(
                        "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?",
                        (quantity, user_id, item_id)
                    )
                else:
                    # 插入新记录
                    await self.conn.execute(
                        "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)",
                        (user_id, item_id, quantity)
                    )
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"添加物品失败: {e}")
            return False
    
    async def remove_item_from_inventory(self, user_id: str, item_id: str, quantity: int = 1) -> bool:
        """从背包移除物品"""
        try:
            # 检查是否有足够数量
            async with self.conn.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            ) as cursor:
                row = await cursor.fetchone()
                if not row or row[0] < quantity:
                    return False
                
                if row[0] == quantity:
                    # 删除记录
                    await self.conn.execute(
                        "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id)
                    )
                else:
                    # 更新数量
                    await self.conn.execute(
                        "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                        (quantity, user_id, item_id)
                    )
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"移除物品失败: {e}")
            return False
    
    # 战斗日志相关操作
    async def add_combat_log(self, log: CombatLog) -> bool:
        """添加战斗日志"""
        try:
            import json
            await self.conn.execute(
                """
                INSERT INTO combat_logs (
                    log_id, attacker_id, defender_id, result, damage, 
                    experience_gained, gold_gained, timestamp, drop_items
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.log_id, log.attacker_id, log.defender_id, log.result,
                    log.damage, log.experience_gained, log.gold_gained,
                    log.timestamp, json.dumps(log.drop_items)
                )
            )
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"添加战斗日志失败: {e}")
            return False
            
    # 后台管理相关方法
    async def get_all_players(self) -> List[Player]:
        """获取所有玩家信息"""
        try:
            async with self.conn.execute("SELECT * FROM players") as cursor:
                rows = await cursor.fetchall()
                players = []
                for row in rows:
                    import json
                    players.append(Player(
                        user_id=row[0],
                        name=row[1],
                        level_index=row[2],
                        experience=row[3],
                        spiritual_root=row[4],
                        max_hp=row[5],
                        current_hp=row[6],
                        attack=row[7],
                        defense=row[8],
                        spirit=row[9],
                        gold=row[10],
                        last_sign_in=row[11],
                        create_time=row[12],
                        update_time=row[13],
                        sect_id=row[14],
                        sect_position=row[15],
                        gongfa_id=row[16],
                        equipment_ids=json.loads(row[17])
                    ))
                return players
        except Exception as e:
            print(f"获取所有玩家失败: {e}")
            return []
            
    async def get_all_items(self) -> List[Item]:
        """获取所有物品信息"""
        try:
            async with self.conn.execute("SELECT * FROM items") as cursor:
                rows = await cursor.fetchall()
                items = []
                for row in rows:
                    import json
                    items.append(Item(
                        item_id=row[0],
                        name=row[1],
                        description=row[2],
                        item_type=row[3],
                        quality=row[4],
                        effect=row[5],
                        price=row[6],
                        max_stack=row[7],
                        usage_requirements=json.loads(row[8])
                    ))
                return items
        except Exception as e:
            print(f"获取所有物品失败: {e}")
            return []
            
    async def get_all_gongfas(self) -> List:
        """获取所有功法信息"""
        try:
            async with self.conn.execute("SELECT * FROM gongfas") as cursor:
                rows = await cursor.fetchall()
                gongfas = []
                for row in rows:
                    import json
                    gongfas.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "type": row[3],
                        "level": row[4],
                        "attack_bonus": row[5],
                        "defense_bonus": row[6],
                        "spirit_bonus": row[7],
                        "hp_bonus": row[8],
                        "required_level": row[9],
                        "price": row[10],
                        "quality": row[11]
                    })
                return gongfas
        except Exception as e:
            print(f"获取所有功法失败: {e}")
            return []
            
    async def get_all_equipments(self) -> List:
        """获取所有装备信息"""
        try:
            async with self.conn.execute("SELECT * FROM equipments") as cursor:
                rows = await cursor.fetchall()
                equipments = []
                for row in rows:
                    import json
                    equipments.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "slot": row[3],
                        "quality": row[4],
                        "attack": row[5],
                        "defense": row[6],
                        "spirit": row[7],
                        "max_hp": row[8],
                        "durability": row[9],
                        "price": row[10],
                        "required_level": row[11],
                        "required_spiritual_root": row[12]
                    })
                return equipments
        except Exception as e:
            print(f"获取所有装备失败: {e}")
            return []
            
    async def get_all_sects(self) -> List:
        """获取所有宗门信息"""
        try:
            async with self.conn.execute("SELECT * FROM sects") as cursor:
                rows = await cursor.fetchall()
                sects = []
                for row in rows:
                    # 获取宗主昵称
                    master_nickname = ""
                    if row[2]:
                        async with self.conn.execute(
                            "SELECT name FROM players WHERE user_id = ?", (row[2],)
                        ) as cursor2:
                            master_row = await cursor2.fetchone()
                            if master_row:
                                master_nickname = master_row[0]
                    
                    # 获取成员数量
                    async with self.conn.execute(
                        "SELECT COUNT(*) FROM players WHERE sect_id = ?", (row[0],)
                    ) as cursor2:
                        member_count_row = await cursor2.fetchone()
                        member_count = member_count_row[0] if member_count_row else 0
                    
                    sects.append({
                        "id": row[0],
                        "name": row[1],
                        "master_id": row[2],
                        "master_nickname": master_nickname,
                        "level": row[3],
                        "experience": row[4],
                        "member_count": member_count,
                        "created_at": row[5]
                    })
                return sects
        except Exception as e:
            print(f"获取所有宗门失败: {e}")
            return []