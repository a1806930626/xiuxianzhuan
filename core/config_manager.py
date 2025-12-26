import json
import os
from pathlib import Path
from typing import Dict, List, Any


class ConfigManager:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)
        self.config_dir = self.plugin_dir / "config"
        
        # 加载配置文件
        self.level_config: List[Dict] = []
        self.items: Dict[str, Dict] = {}
        self.monsters: Dict[str, Dict] = {}
        self.sects: Dict[str, Dict] = {}
        self.bosses: Dict[str, Dict] = {}
        
        self._load_configs()
    
    def _load_configs(self):
        """加载所有配置文件"""
        try:
            # 加载境界配置
            level_path = self.config_dir / "level_config.json"
            if level_path.exists():
                with open(level_path, "r", encoding="utf-8") as f:
                    self.level_config = json.load(f)
            else:
                # 使用默认配置
                self.level_config = self._get_default_level_config()
            
            # 加载物品配置
            items_path = self.config_dir / "items.json"
            if items_path.exists():
                with open(items_path, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            else:
                self.items = self._get_default_items()
            
            # 加载怪物配置
            monsters_path = self.config_dir / "monsters.json"
            if monsters_path.exists():
                with open(monsters_path, "r", encoding="utf-8") as f:
                    self.monsters = json.load(f)
            else:
                self.monsters = self._get_default_monsters()
            
            # 加载宗门配置
            sects_path = self.config_dir / "sects.json"
            if sects_path.exists():
                with open(sects_path, "r", encoding="utf-8") as f:
                    self.sects = json.load(f)
            else:
                self.sects = self._get_default_sects()
            
            # 加载boss配置
            bosses_path = self.config_dir / "bosses.json"
            if bosses_path.exists():
                with open(bosses_path, "r", encoding="utf-8") as f:
                    self.bosses = json.load(f)
            else:
                self.bosses = self._get_default_bosses()
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            # 使用默认配置
            self.level_config = self._get_default_level_config()
            self.items = self._get_default_items()
            self.monsters = self._get_default_monsters()
            self.sects = self._get_default_sects()
            self.bosses = self._get_default_bosses()
    
    def _get_default_level_config(self) -> List[Dict]:
        """获取默认境界配置"""
        return [
            {"name": "练气初期", "experience": 0},
            {"name": "练气中期", "experience": 100},
            {"name": "练气后期", "experience": 300},
            {"name": "筑基初期", "experience": 600},
            {"name": "筑基中期", "experience": 1000},
            {"name": "筑基后期", "experience": 1500}
        ]
    
    def _get_default_items(self) -> Dict[str, Dict]:
        """获取默认物品配置"""
        return {
            "hp_potion": {
                "name": "气血丹",
                "description": "恢复50点生命值",
                "type": "consumable",
                "price": 50,
                "effects": {"hp": 50}
            },
            "spirit_potion": {
                "name": "灵力丹",
                "description": "恢复20点灵力",
                "type": "consumable",
                "price": 80,
                "effects": {"spirit": 20}
            },
            "iron_sword": {
                "name": "铁剑",
                "description": "普通的铁剑，增加10点攻击力",
                "type": "equipment",
                "price": 200,
                "effects": {"attack": 10}
            },
            "leather_armor": {
                "name": "皮甲",
                "description": "普通的皮甲，增加5点防御力",
                "type": "equipment",
                "price": 150,
                "effects": {"defense": 5}
            }
        }
    
    def _get_default_monsters(self) -> Dict[str, Dict]:
        """获取默认怪物配置"""
        return {
            "goblin": {
                "name": "小妖精",
                "level": 0,
                "max_hp": 50,
                "attack": 8,
                "defense": 2,
                "spirit": 3,
                "experience": 20,
                "gold": 10,
                "drop_items": [{"item_id": "hp_potion", "probability": 0.3}]
            },
            "wolf": {
                "name": "野狼",
                "level": 1,
                "max_hp": 80,
                "attack": 12,
                "defense": 4,
                "spirit": 2,
                "experience": 35,
                "gold": 20,
                "drop_items": [{"item_id": "hp_potion", "probability": 0.5}]
            }
        }
    
    def _get_default_sects(self) -> Dict[str, Dict]:
        """获取默认宗门配置"""
        return {
            "qingyun": {
                "name": "青云门",
                "description": "正道第一大派，擅长剑术",
                "required_level": 2
            },
            "hehuan": {
                "name": "合欢宗",
                "description": "修炼男女双休之法的门派",
                "required_level": 2
            }
        }
    
    def _get_default_bosses(self) -> Dict[str, Dict]:
        """获取默认Boss配置"""
        return {
            "demon_lord": {
                "name": "魔王",
                "level": 5,
                "max_hp": 500,
                "attack": 50,
                "defense": 20,
                "spirit": 30,
                "experience": 1000,
                "gold": 500,
                "drop_items": [{"item_id": "iron_sword", "probability": 1.0}]
            }
        }