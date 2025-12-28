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
    
    def _calculate_upgrade_exp_by_realm(self, realm_name: str) -> int:
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
                    spiritual_root=row[4],
                    max_hp=row[5],
                    current_hp=row[6],
                    attack=row[7],
                    defense=row[8],
                    speed=row[9],
                    spirit=row[10],
                    spirit_stone=row[11],
                    last_sign_in=row[12],
                    create_time=row[13],
                    update_time=row[14],
                    sect_id=row[15],
                    sect_position=row[16],
                    gongfa_ids=json.loads(row[17]),  # 更新为gongfa_ids
                    equipment_ids=json.loads(row[18])
                )
            return None
    
    async def create_player(self, player: Player) -> bool:
        """创建新玩家"""
        try:
            import json
            await self.conn.execute(
                """
                INSERT INTO players (
                    user_id, name, level_index, spiritual_root, 
                    max_hp, current_hp, attack, defense, speed, spirit_stone, 
                    last_sign_in, create_time, update_time, sect_id, 
                    sect_position, gongfa_ids, equipment_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    player.user_id, player.name, player.level_index,
                    player.spiritual_root, player.max_hp, player.current_hp, player.attack,
                    player.defense, player.speed, player.spirit_stone, player.last_sign_in,
                    player.create_time, player.update_time, player.sect_id,
                    player.sect_position, json.dumps(player.gongfa_ids), json.dumps(player.equipment_ids)
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
                    name = ?, level_index = ?, spiritual_root = ?, 
                    max_hp = ?, current_hp = ?, attack = ?, defense = ?, speed = ?, 
                    spirit_stone = ?, last_sign_in = ?, update_time = ?, sect_id = ?, 
                    sect_position = ?, gongfa_ids = ?, equipment_ids = ?
                WHERE user_id = ?
                """,
                (
                    player.name, player.level_index, player.spiritual_root,
                    player.max_hp, player.current_hp, player.attack, player.defense,
                    player.speed, player.spirit_stone, player.last_sign_in,
                    player.update_time, player.sect_id, player.sect_position, json.dumps(player.gongfa_ids),
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
                    spirit_stone_gained, timestamp, drop_items
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.log_id, log.attacker_id, log.defender_id, log.result,
                    log.damage, log.spirit_stone_gained,
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
                        spiritual_root=row[4],
                        max_hp=row[5],
                        current_hp=row[6],
                        attack=row[7],
                        defense=row[8],
                        speed=row[9],
                        spirit=row[10],
                        spirit_stone=row[11],
                        last_sign_in=row[12],
                        create_time=row[13],
                        update_time=row[14],
                        sect_id=row[15],
                        sect_position=row[16],
                        gongfa_ids=json.loads(row[17]),  # 更新为gongfa_ids
                        equipment_ids=json.loads(row[18])
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
            
    async def get_gongfa_by_id(self, gongfa_id: str) -> Optional[Dict]:
        """根据功法ID获取功法信息"""
        try:
            async with self.conn.execute(
                "SELECT * FROM gongfas WHERE id = ?", (gongfa_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "upgrade_exp": row[2],
                        "attack_bonus": row[3],
                        "hp_bonus": row[4],
                        "defense_bonus": row[5],
                        "speed_bonus": row[6],
                        "cultivation_speed_bonus": row[7]
                    }
                return None
        except Exception as e:
            print(f"获取功法失败: {e}")
            return None
    
    async def get_gongfas_by_ids(self, gongfa_ids: List[str]) -> List[Dict]:
        """根据功法ID列表获取功法信息列表"""
        if not gongfa_ids:
            return []
        
        placeholders = ','.join(['?' for _ in gongfa_ids])
        try:
            async with self.conn.execute(
                f"SELECT * FROM gongfas WHERE id IN ({placeholders})", gongfa_ids
            ) as cursor:
                rows = await cursor.fetchall()
                gongfas = []
                for row in rows:
                    gongfas.append({
                        "id": row[0],
                        "name": row[1],
                        "upgrade_exp": row[2],
                        "attack_bonus": row[3],
                        "hp_bonus": row[4],
                        "defense_bonus": row[5],
                        "speed_bonus": row[6],
                        "cultivation_speed_bonus": row[7]
                    })
                return gongfas
        except Exception as e:
            print(f"获取功法列表失败: {e}")
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
                        "upgrade_exp": row[2],
                        "attack_bonus": row[3],
                        "hp_bonus": row[4],
                        "defense_bonus": row[5],
                        "speed_bonus": row[6],
                        "cultivation_speed_bonus": row[7]
                    })
                return gongfas
        except Exception as e:
            print(f"获取所有功法失败: {e}")
            return []
            
    async def get_item_by_id(self, item_id: str) -> Optional[Dict]:
        """根据物品ID获取物品信息"""
        try:
            # 首先尝试从equipments表中获取
            async with self.conn.execute(
                "SELECT * FROM equipments WHERE id = ?", (item_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "item_id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "slot": row[3],
                        "base_attack": row[4],
                        "base_defense": row[5],
                        "base_speed": row[6],
                        "base_hp": row[7],
                        "base_spirit": row[8],
                        "upgrade_level": row[9],
                        "quality": row[10],
                        "price": row[11],
                        "required_realm": row[12],
                        "type": "equipment"
                    }
            # 如果在equipments表中没找到，尝试从items表中获取
            async with self.conn.execute(
                "SELECT * FROM items WHERE item_id = ?", (item_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    import json
                    item_data = {
                        "item_id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "type": row[3],
                        "quality": row[4],
                        "effect": row[5],
                        "price": row[6],
                        "max_stack": row[7],
                        "usage_requirements": json.loads(row[8]),
                        "upgrade_level": row[9] if len(row) > 9 else 0,
                        "base_attack": row[10] if len(row) > 10 else 0,
                        "base_defense": row[11] if len(row) > 11 else 0,
                        "base_speed": row[12] if len(row) > 12 else 0,
                        "base_hp": row[13] if len(row) > 13 else 0,
                        "base_spirit": row[14] if len(row) > 14 else 0
                    }
                    
                    # 如果是consumable类型的物品，尝试从danyao表获取效果
                    if item_data["type"] == "consumable":
                        danyao_data = await self.get_danyao_by_id(item_id)
                        if danyao_data:
                            # 使用danyao表中的效果，而不是items表中的效果
                            item_data["effect"] = json.dumps(danyao_data["effect"])
                    
                    return item_data
            return None
        except Exception as e:
            print(f"获取物品失败: {e}")
            return None
    
    async def update_item(self, item_id: str, item_data: Dict) -> bool:
        """更新物品信息"""
        try:
            # 如果是装备，更新equipments表
            if item_data.get("type") == "equipment":
                await self.conn.execute("""
                    UPDATE equipments SET 
                        name = ?, description = ?, slot = ?, base_attack = ?, base_defense = ?, 
                        base_speed = ?, base_hp = ?, base_spirit = ?, upgrade_level = ?, quality = ?, 
                        price = ?, required_realm = ?
                    WHERE id = ?
                """, (
                    item_data.get("name"), item_data.get("description"), 
                    item_data.get("slot"), item_data.get("base_attack", 0),
                    item_data.get("base_defense", 0), item_data.get("base_speed", 0),
                    item_data.get("base_hp", 0), item_data.get("base_spirit", 0),
                    item_data.get("upgrade_level", 0), item_data.get("quality"),
                    item_data.get("price"), item_data.get("required_realm", 0),
                    item_id
                ))
            else:
                # 如果是普通物品，更新items表
                import json
                # 对于consumable类型的物品，effect存储在danyao表中，items表中effect字段设为空
                effect_value = item_data.get("effect") if item_data.get("type") != "consumable" else ""
                
                await self.conn.execute("""
                    UPDATE items SET 
                        name = ?, description = ?, type = ?, quality = ?, 
                        effect = ?, price = ?, max_stack = ?, usage_requirements = ?,
                        upgrade_level = ?, base_attack = ?, base_defense = ?,
                        base_speed = ?, base_hp = ?, base_spirit = ?
                    WHERE item_id = ?
                """, (
                    item_data.get("name"), item_data.get("description"), 
                    item_data.get("type"), item_data.get("quality"),
                    effect_value,  # 对于consumable，这里会是空字符串，效果存储在danyao表中
                    item_data.get("price"),
                    item_data.get("max_stack"), json.dumps(item_data.get("usage_requirements", {})),
                    item_data.get("upgrade_level", 0), item_data.get("base_attack", 0),
                    item_data.get("base_defense", 0), item_data.get("base_speed", 0),
                    item_data.get("base_hp", 0), item_data.get("base_spirit", 0),
                    item_id
                ))
                
                # 如果是consumable类型的物品，同时更新danyao表
                if item_data.get("type") == "consumable":
                    # 检查danyao表中是否已存在该物品
                    danyao_cursor = await self.conn.execute("SELECT id FROM danyao WHERE id = ?", (item_id,))
                    danyao_existing = await danyao_cursor.fetchone()
                    
                    if danyao_existing:
                        # 更新danyao表
                        effects = item_data.get("effects", {}) or json.loads(item_data.get("effect", "{}"))
                        await self.conn.execute("""
                        UPDATE danyao SET 
                            name = ?, effect = ?
                        WHERE id = ?
                        """, (
                            item_data.get("name", ""),
                            json.dumps(effects),  # 将效果存储为JSON字符串
                            item_id
                        ))
                    else:
                        # 插入到danyao表
                        effects = item_data.get("effects", {}) or json.loads(item_data.get("effect", "{}"))
                        await self.conn.execute("""
                        INSERT INTO danyao 
                        (id, name, effect)
                        VALUES (?, ?, ?)
                        """, (
                            item_id,
                            item_data.get("name", ""),
                            json.dumps(effects)  # 将效果存储为JSON字符串
                        ))
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"更新物品失败: {e}")
            return False
            
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
    
    async def sync_items_to_database(self, items_config: Dict[str, Dict]):
        """将items.json中的物品配置同步到数据库中"""
        try:
            for item_id, item_data in items_config.items():
                # 根据物品类型决定如何处理
                item_type = item_data.get("type", "consumable")
                
                if item_type == "gongfa":
                    # 对于功法类型，添加到gongfas表
                    # 检查功法是否已存在
                    cursor = await self.conn.execute("SELECT id FROM gongfas WHERE id = ?", (item_id,))
                    existing = await cursor.fetchone()
                    
                    if not existing:
                        # 如果不存在，则插入新的功法
                        await self.conn.execute("""
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
                
                elif item_type == "gongfa_book":
                    # 对于功法秘籍，添加到items表
                    cursor = await self.conn.execute("SELECT item_id FROM items WHERE item_id = ?", (item_id,))
                    existing = await cursor.fetchone()
                    
                    if not existing:
                        # 如果不存在，则插入新的功法秘籍
                        import json
                        category = "功法"
                        await self.conn.execute("""
                        INSERT INTO items 
                        (item_id, name, description, item_type, category, quality, effect, price, max_stack, usage_requirements) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            item_id,
                            item_data.get("name", ""),
                            item_data.get("description", ""),
                            item_type,
                            category,
                            item_data.get("quality", "common"),
                            str({}),  # 功法秘籍没有效果
                            item_data.get("price", 0),
                            item_data.get("max_stack", 99),
                            json.dumps({"required_realm": item_data.get("required_realm", 0)})
                        ))
                
                elif item_type in ["consumable", "equipment"]:
                    # 对于消耗品和装备，添加到items表
                    cursor = await self.conn.execute("SELECT item_id FROM items WHERE item_id = ?", (item_id,))
                    existing = await cursor.fetchone()
                    
                    if not existing:
                        import json
                        category = "丹药" if item_type == "consumable" else "装备"
                        
                        # 对于consumable类型的物品，effect存储在danyao表中，items表中effect字段设为空
                        effect = str(item_data.get("effects", {})) if item_type != "consumable" else ""
                        
                        await self.conn.execute("""
                        INSERT INTO items 
                        (item_id, name, description, item_type, category, quality, effect, price, max_stack, usage_requirements) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            item_id,
                            item_data.get("name", ""),
                            item_data.get("description", ""),
                            item_type,
                            category,
                            item_data.get("quality", "common"),
                            effect,  # 对于consumable，这里会是空字符串，效果存储在danyao表中
                            item_data.get("price", 0),
                            item_data.get("max_stack", 99),
                            json.dumps(item_data.get("usage_requirements", {}))
                        ))
                        
                        # 如果是consumable类型的物品，同时添加到danyao表
                        if item_type == "consumable":
                            # 检查danyao表中是否已存在该物品
                            danyao_cursor = await self.conn.execute("SELECT id FROM danyao WHERE id = ?", (item_id,))
                            danyao_existing = await danyao_cursor.fetchone()
                            
                            if not danyao_existing:
                                # 添加到danyao表
                                effects = item_data.get("effects", {})
                                await self.conn.execute("""
                                INSERT INTO danyao 
                                (id, name, effect)
                                VALUES (?, ?, ?)
                                """, (
                                    item_id,
                                    item_data.get("name", ""),
                                    json.dumps(effects)  # 将效果存储为JSON字符串
                                ))
                
                # 对于其他类型的物品，也尝试添加到items表
                else:
                    cursor = await self.conn.execute("SELECT item_id FROM items WHERE item_id = ?", (item_id,))
                    existing = await cursor.fetchone()
                    
                    if not existing:
                        import json
                        category = item_data.get("category", "")
                        if not category:
                            if item_type == "consumable":
                                category = "丹药"
                            elif item_type == "equipment":
                                category = "装备"
                            elif item_type == "gongfa_book":
                                category = "功法"
                            else:
                                category = "其他"
                        
                        # 对于consumable类型的物品，effect存储在danyao表中，items表中effect字段设为空
                        effect = str(item_data.get("effects", {})) if item_type != "consumable" else ""
                        
                        await self.conn.execute("""
                        INSERT INTO items 
                        (item_id, name, description, item_type, category, quality, effect, price, max_stack, usage_requirements) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            item_id,
                            item_data.get("name", ""),
                            item_data.get("description", ""),
                            item_type,
                            category,
                            item_data.get("quality", "common"),
                            effect,
                            item_data.get("price", 0),
                            item_data.get("max_stack", 99),
                            json.dumps(item_data.get("usage_requirements", {}))
                        ))
                        
                        # 如果是consumable类型的物品，同时添加到danyao表
                        if item_type == "consumable":
                            # 检查danyao表中是否已存在该物品
                            danyao_cursor = await self.conn.execute("SELECT id FROM danyao WHERE id = ?", (item_id,))
                            danyao_existing = await danyao_cursor.fetchone()
                            
                            if not danyao_existing:
                                # 添加到danyao表
                                effects = item_data.get("effects", {})
                                await self.conn.execute("""
                                INSERT INTO danyao 
                                (id, name, effect)
                                VALUES (?, ?, ?)
                                """, (
                                    item_id,
                                    item_data.get("name", ""),
                                    json.dumps(effects)  # 将效果存储为JSON字符串
                                ))
            
            await self.conn.commit()
            print("物品配置已同步到数据库")
            return True
        except Exception as e:
            print(f"同步物品配置到数据库失败: {e}")
            return False
    
    async def get_danyao_by_id(self, danyao_id: str) -> Optional[Dict]:
        """根据ID获取丹药信息"""
        async with self.conn.execute(
            "SELECT id, name, effect FROM danyao WHERE id = ?", (danyao_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                import json
                return {
                    "id": row[0],
                    "name": row[1],
                    "effect": json.loads(row[2]) if row[2] else {}
                }
            return None
    
    async def get_danyao_by_name(self, danyao_name: str) -> Optional[Dict]:
        """根据名称获取丹药信息"""
        async with self.conn.execute(
            "SELECT id, name, effect FROM danyao WHERE name = ?", (danyao_name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                import json
                return {
                    "id": row[0],
                    "name": row[1],
                    "effect": json.loads(row[2]) if row[2] else {}
                }
            return None
    
    async def get_all_danyao(self) -> List[Dict]:
        """获取所有丹药信息"""
        async with self.conn.execute(
            "SELECT id, name, effect FROM danyao"
        ) as cursor:
            rows = await cursor.fetchall()
            import json
            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "name": row[1],
                    "effect": json.loads(row[2]) if row[2] else {}
                })
            return result

    async def get_sect_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取宗门信息"""
        async with self.conn.execute(
            "SELECT id, name, leader_id, level, experience, created_at FROM sects WHERE name = ?", (name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "leader_id": row[2],
                    "level": row[3],
                    "experience": row[4],
                    "created_at": row[5]
                }
            return None

    async def get_sect_by_id(self, sect_id: str) -> Optional[Dict]:
        """根据ID获取宗门信息"""
        async with self.conn.execute(
            "SELECT id, name, leader_id, level, experience, created_at FROM sects WHERE id = ?", (sect_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "leader_id": row[2],
                    "level": row[3],
                    "experience": row[4],
                    "created_at": row[5]
                }
            return None

    async def create_sect(self, name: str, leader_id: str) -> str:
        """创建宗门"""
        import uuid
        sect_id = str(uuid.uuid4())
        
        await self.conn.execute("""
        INSERT INTO sects (id, name, leader_id, level, experience)
        VALUES (?, ?, ?, 1, 0)
        """, (sect_id, name, leader_id))
        
        await self.conn.commit()
        return sect_id

    async def delete_sect(self, sect_id: str) -> bool:
        """删除宗门"""
        try:
            await self.conn.execute("DELETE FROM sects WHERE id = ?", (sect_id,))
            await self.conn.commit()
            return True
        except Exception as e:
            print(f"删除宗门失败: {e}")
            return False

    async def get_sect_members(self, sect_id: str) -> List[Dict]:
        """获取宗门成员列表"""
        async with self.conn.execute(
            "SELECT user_id, name FROM players WHERE sect_id = ?", (sect_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            members = []
            for row in rows:
                members.append({
                    "user_id": row[0],
                    "name": row[1]
                })
            return members