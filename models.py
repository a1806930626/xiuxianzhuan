from dataclasses import dataclass
from typing import Dict, List, Optional
import json


@dataclass
class Player:
    user_id: str
    name: str = "修仙者"
    level_index: int = 0
    spiritual_root: str = "未知"
    max_hp: int = 100
    current_hp: int = 100
    attack: int = 10
    defense: int = 5
    speed: int = 0  # 速度属性
    spirit: int = 5  # 灵气值（用于升级等）
    spirit_stone: int = 100
    last_sign_in: str = ""
    create_time: str = ""
    update_time: str = ""
    sect_id: Optional[str] = None
    sect_position: str = ""
    gongfa_ids: List[str] = None  # 功法ID列表，最多5个
    equipment_ids: Dict[str, str] = None  # 装备位置: 装备ID
    
    def __post_init__(self):
        if self.equipment_ids is None:
            self.equipment_ids = {
                "weapon": "",
                "armor": "",
                "shoes": "",
                "accessory": ""
            }
        if self.gongfa_ids is None:
            self.gongfa_ids = []
    
    def get_level(self, level_config: List[Dict]) -> Dict:
        """获取当前境界信息"""
        if self.level_index < len(level_config):
            return level_config[self.level_index]
        return level_config[-1]
    
    def get_combat_stats(self, items: Dict[str, Dict], gongfas: List[Dict] = None) -> Dict:
        """获取包含装备和功法加成的战斗属性"""
        stats = {
            "hp": self.max_hp,
            "attack": self.attack,
            "defense": self.defense,
            "speed": self.speed,
            "spirit": self.spirit
        }
        
        # 计算装备加成
        for pos, item_id in self.equipment_ids.items():
            if item_id and item_id in items:
                item = items[item_id]
                # 从装备获取基础属性
                stats["hp"] += item.get("hp", 0) + item.get("base_hp", 0)
                stats["attack"] += item.get("attack", 0) + item.get("base_attack", 0)
                stats["defense"] += item.get("defense", 0) + item.get("base_defense", 0)
                stats["speed"] += item.get("speed", 0) + item.get("base_speed", 0)
                stats["spirit"] += item.get("spirit", 0) + item.get("base_spirit", 0)
        
        # 计算功法加成
        if gongfas:
            for gongfa in gongfas:
                stats["hp"] += gongfa.get("hp_bonus", 0)
                stats["attack"] += gongfa.get("attack_bonus", 0)
                stats["defense"] += gongfa.get("defense_bonus", 0)
                stats["speed"] += gongfa.get("speed_bonus", 0)
        
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
    required_realm: int
    members: List[str] = None
    
    def __post_init__(self):
        if self.members is None:
            self.members = []


@dataclass
class Monster:
    monster_id: str
    name: str
    max_hp: int
    attack: int
    defense: int
    spirit_stone: int
    speed: int = 0  # 速度属性
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
    spirit_stone_gained: int
    timestamp: str
    drop_items: List[Dict] = None
    
    def __post_init__(self):
        if self.drop_items is None:
            self.drop_items = []