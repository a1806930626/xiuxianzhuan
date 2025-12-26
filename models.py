from dataclasses import dataclass
from typing import Dict, List, Optional
import json


@dataclass
class Player:
    user_id: str
    name: str = "修仙者"
    level_index: int = 0
    experience: int = 0
    spiritual_root: str = "未知"
    max_hp: int = 100
    current_hp: int = 100
    attack: int = 10
    defense: int = 5
    spirit: int = 5
    gold: int = 100
    last_sign_in: str = ""
    create_time: str = ""
    update_time: str = ""
    sect_id: Optional[str] = None
    sect_position: str = ""
    gongfa_id: Optional[str] = None
    equipment_ids: Dict[str, str] = None  # 装备位置: 装备ID
    
    def __post_init__(self):
        if self.equipment_ids is None:
            self.equipment_ids = {
                "weapon": "",
                "armor": "",
                "accessory1": "",
                "accessory2": ""
            }
    
    def get_level(self, level_config: List[Dict]) -> Dict:
        """获取当前境界信息"""
        if self.level_index < len(level_config):
            return level_config[self.level_index]
        return level_config[-1]
    
    def get_combat_stats(self, items: Dict[str, Dict]) -> Dict:
        """获取包含装备加成的战斗属性"""
        stats = {
            "hp": self.max_hp,
            "attack": self.attack,
            "defense": self.defense,
            "spirit": self.spirit
        }
        
        # 计算装备加成
        for pos, item_id in self.equipment_ids.items():
            if item_id and item_id in items:
                item = items[item_id]
                stats["hp"] += item.get("hp", 0)
                stats["attack"] += item.get("attack", 0)
                stats["defense"] += item.get("defense", 0)
                stats["spirit"] += item.get("spirit", 0)
        
        return stats


@dataclass
class Item:
    item_id: str
    name: str
    description: str
    type: str  # consumable, equipment, material
    price: int
    effects: Dict = None
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = {}


@dataclass
class Gongfa:
    gongfa_id: str
    name: str
    description: str
    level: int
    effects: Dict = None
    
    def __post_init__(self):
        if self.effects is None:
            self.effects = {}


@dataclass
class Sect:
    sect_id: str
    name: str
    description: str
    required_level: int
    members: List[str] = None
    
    def __post_init__(self):
        if self.members is None:
            self.members = []


@dataclass
class Monster:
    monster_id: str
    name: str
    level: int
    max_hp: int
    attack: int
    defense: int
    spirit: int
    experience: int
    gold: int
    drop_items: List[Dict] = None  # [{'item_id': 'xxx', 'probability': 0.5}]
    
    def __post_init__(self):
        if self.drop_items is None:
            self.drop_items = []


@dataclass
class InventoryItem:
    user_id: str
    item_id: str
    quantity: int = 1


@dataclass
class CombatLog:
    log_id: str
    attacker_id: str
    defender_id: str
    result: str  # win, lose
    damage: int
    experience_gained: int
    gold_gained: int
    timestamp: str
    drop_items: List[str] = None
    
    def __post_init__(self):
        if self.drop_items is None:
            self.drop_items = []