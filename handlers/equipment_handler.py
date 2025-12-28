import random
from typing import Dict, List, Optional
from astrbot.api.event import AstrMessageEvent
from ..data.data_manager import DataBase
from ..core.config_manager import ConfigManager
from ..models import Player


class EquipmentHandler:
    """装备相关命令处理"""
    
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_equipment(self, event: AstrMessageEvent):
        """查看装备信息"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取装备信息
        equipment_info = await self.get_equipment_info(player)
        
        # 构建回复消息
        msg = f"「{player.name}」的装备信息：\n"
        msg += f"武器：{equipment_info.get('weapon', '无')}\n"
        msg += f"护甲：{equipment_info.get('armor', '无')}\n"
        msg += f"鞋子：{equipment_info.get('shoes', '无')}\n"
        msg += f"饰品：{equipment_info.get('accessory', '无')}\n"
        
        yield msg

    async def handle_wear_equipment(self, event: AstrMessageEvent):
        """穿戴装备"""
        user_id = str(event.get_author_id())
        message = event.get_content().strip()
        
        # 解析装备ID
        parts = message.split()
        if len(parts) < 2:
            yield "请指定要穿戴的装备ID，格式：穿戴 [装备ID]"
            return
            
        equipment_id = parts[1]
        
        player = await self.db.get_player_by_id(user_id)
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 检查玩家背包中是否有该装备
        inventory = await self.db.get_player_inventory(user_id)
        equipment_in_inventory = None
        for item in inventory:
            if item.item_id == equipment_id:
                equipment_in_inventory = item
                break
        
        if not equipment_in_inventory:
            yield f"背包中没有找到ID为 {equipment_id} 的装备。"
            return
        
        # 获取装备详细信息
        equipment = await self.db.get_item_by_id(equipment_id)
        if not equipment or equipment.type != "equipment":
            yield f"找不到装备 {equipment_id} 或该物品不是装备。"
            return
        
        # 获取装备位置
        equipment_slot = equipment.get("slot", "unknown")
        
        # 对于饰品槽位，检查是否已经穿戴了相同ID的饰品
        if equipment_slot == "accessory":
            # 检查饰品槽位是否已经有相同ID的饰品
            if player.equipment_ids.get("accessory") == equipment_id:
                yield f"您已经穿戴了ID为 {equipment_id} 的饰品，不能重复佩戴。"
                return
        
        # 检查是否已有装备在该位置
        old_equipment_id = player.equipment_ids.get(equipment_slot)
        if old_equipment_id:
            # 先将旧装备放回背包
            await self.db.add_item_to_inventory(user_id, old_equipment_id, 1)
        
        # 穿戴新装备
        player.equipment_ids[equipment_slot] = equipment_id
        
        # 从背包中移除装备
        await self.db.remove_item_from_inventory(user_id, equipment_id, 1)
        
        # 保存玩家信息
        await self.db.update_player(player)
        
        yield f"成功穿戴装备 {equipment.get('name', equipment_id)} 到 {self.get_slot_name(equipment_slot)} 位置。"

    async def handle_equip_upgrade(self, event: AstrMessageEvent):
        """强化装备"""
        user_id = str(event.get_author_id())
        message = event.get_content().strip()
        
        # 解析装备ID
        parts = message.split()
        if len(parts) < 2:
            yield "请指定要强化的装备ID，格式：强化 [装备ID]"
            return
            
        equipment_id = parts[1]
        
        player = await self.db.get_player_by_id(user_id)
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 检查装备是否在穿戴中
        is_equipped = False
        equipped_slot = None
        for slot, equipped_id in player.equipment_ids.items():
            if equipped_id == equipment_id:
                is_equipped = True
                equipped_slot = slot
                break
        
        if not is_equipped:
            yield f"装备 {equipment_id} 没有被穿戴，无法强化。"
            return
        
        # 获取装备详细信息
        equipment = await self.db.get_item_by_id(equipment_id)
        if not equipment or equipment.type != "equipment":
            yield f"找不到装备 {equipment_id} 或该物品不是装备。"
            return
        
        # 获取当前强化等级
        current_upgrade_level = equipment.get("upgrade_level", 0)
        
        # 检查是否已达到最高强化等级
        if current_upgrade_level >= 99:
            yield f"装备 {equipment_id} 已达到最高强化等级99级，无法继续强化。"
            return
        
        # 计算强化成功率
        base_success_rate = 100  # 初始成功率100%
        success_rate = max(1, base_success_rate - (current_upgrade_level * 20))  # 每成功1级减少20%成功率，最低1%
        
        # 执行强化
        if random.randint(1, 100) <= success_rate:
            # 强化成功
            new_upgrade_level = current_upgrade_level + 1
            
            # 更新装备信息
            equipment["upgrade_level"] = new_upgrade_level
            equipment["attack"] = equipment.get("base_attack", 0) + int(equipment.get("base_attack", 0) * new_upgrade_level * 0.1)
            equipment["defense"] = equipment.get("base_defense", 0) + int(equipment.get("base_defense", 0) * new_upgrade_level * 0.1)
            equipment["speed"] = equipment.get("base_speed", 0) + int(equipment.get("base_speed", 0) * new_upgrade_level * 0.1)
            equipment["hp"] = equipment.get("base_hp", 0) + int(equipment.get("base_hp", 0) * new_upgrade_level * 0.1)
            equipment["spirit"] = equipment.get("base_spirit", 0) + int(equipment.get("base_spirit", 0) * new_upgrade_level * 0.01)
            
            await self.db.update_item(equipment_id, equipment)
            
            yield f"装备强化成功！{equipment.get('name', equipment_id)} 已强化至 +{new_upgrade_level} 级！\n当前成功率: {success_rate}%"
        else:
            # 强化失败，装备等级不变
            yield f"装备强化失败！{equipment.get('name', equipment_id)} 仍为 +{current_upgrade_level} 级。\n当前成功率: {success_rate}%"

    async def handle_replace_equipment(self, event: AstrMessageEvent):
        """替换装备（保留强化等级）"""
        user_id = str(event.get_author_id())
        message = event.get_content().strip()
        
        # 解析装备ID
        parts = message.split()
        if len(parts) < 3:
            yield "请指定要替换的装备ID和新装备ID，格式：替换 [原装备ID] [新装备ID]"
            return
            
        old_equipment_id = parts[1]
        new_equipment_id = parts[2]
        
        player = await self.db.get_player_by_id(user_id)
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 检查玩家背包中是否有新装备
        inventory = await self.db.get_player_inventory(user_id)
        new_equipment_in_inventory = None
        for item in inventory:
            if item.item_id == new_equipment_id:
                new_equipment_in_inventory = item
                break
        
        if not new_equipment_in_inventory:
            yield f"背包中没有找到ID为 {new_equipment_id} 的新装备。"
            return
        
        # 获取新装备详细信息
        new_equipment = await self.db.get_item_by_id(new_equipment_id)
        if not new_equipment or new_equipment.type != "equipment":
            yield f"找不到新装备 {new_equipment_id} 或该物品不是装备。"
            return
        
        # 检查原装备是否在穿戴中
        old_equipment_slot = None
        for slot, equipped_id in player.equipment_ids.items():
            if equipped_id == old_equipment_id:
                old_equipment_slot = slot
                break
        
        if not old_equipment_slot:
            yield f"原装备 {old_equipment_id} 没有被穿戴，无法替换。"
            return
        
        # 获取原装备信息
        old_equipment = await self.db.get_item_by_id(old_equipment_id)
        if not old_equipment:
            yield f"找不到原装备 {old_equipment_id}。"
            return
        
        # 获取原装备的强化等级
        old_upgrade_level = old_equipment.get("upgrade_level", 0)
        
        # 将原装备从穿戴中移除
        player.equipment_ids[old_equipment_slot] = ""
        
        # 从背包中移除新装备
        await self.db.remove_item_from_inventory(user_id, new_equipment_id, 1)
        
        # 将新装备设置到相同位置，并应用原装备的强化等级
        new_equipment["upgrade_level"] = old_upgrade_level
        # 重新计算属性加成
        new_equipment["attack"] = new_equipment.get("base_attack", 0) + int(new_equipment.get("base_attack", 0) * old_upgrade_level * 0.1)
        new_equipment["defense"] = new_equipment.get("base_defense", 0) + int(new_equipment.get("base_defense", 0) * old_upgrade_level * 0.1)
        new_equipment["speed"] = new_equipment.get("base_speed", 0) + int(new_equipment.get("base_speed", 0) * old_upgrade_level * 0.1)
        new_equipment["hp"] = new_equipment.get("base_hp", 0) + int(new_equipment.get("base_hp", 0) * old_upgrade_level * 0.1)
        new_equipment["spirit"] = new_equipment.get("base_spirit", 0) + int(new_equipment.get("base_spirit", 0) * old_upgrade_level * 0.01)
        
        # 更新新装备信息
        await self.db.update_item(new_equipment_id, new_equipment)
        
        # 将新装备穿戴到原位置
        player.equipment_ids[old_equipment_slot] = new_equipment_id
        
        # 保存玩家信息
        await self.db.update_player(player)
        
        yield f"成功替换装备！原装备 {old_equipment_id} 的强化等级 +{old_upgrade_level} 已转移到新装备 {new_equipment.get('name', new_equipment_id)}，原装备已消耗。"

    async def get_equipment_info(self, player: Player) -> Dict[str, str]:
        """获取装备信息"""
        equipment_info = {}
        
        for slot, equipment_id in player.equipment_ids.items():
            if equipment_id:
                equipment = await self.db.get_item_by_id(equipment_id)
                if equipment:
                    name = equipment.get('name', equipment_id)
                    upgrade_level = equipment.get('upgrade_level', 0)
                    if upgrade_level > 0:
                        equipment_info[slot] = f"{name}(+{upgrade_level})"
                    else:
                        equipment_info[slot] = name
                else:
                    equipment_info[slot] = "未知装备"
            else:
                equipment_info[slot] = "无"
        
        return equipment_info

    def get_slot_name(self, slot: str) -> str:
        """获取装备位置名称"""
        slot_names = {
            "weapon": "武器",
            "armor": "护甲",
            "shoes": "鞋子",
            "accessory": "饰品"
        }
        return slot_names.get(slot, slot)