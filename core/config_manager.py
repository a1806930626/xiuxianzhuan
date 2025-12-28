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
    
    def reload_items(self):
        """重新加载items配置"""
        try:
            items_path = self.config_dir / "items.json"
            if items_path.exists():
                with open(items_path, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            else:
                self.items = self._get_default_items()
        except Exception as e:
            print(f"重新加载物品配置失败: {e}")
    
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
            self._reset_to_defaults()
    
    def _reset_to_defaults(self):
        """重置所有配置为默认值"""
        self.level_config = self._get_default_level_config()
        self.items = self._get_default_items()
        self.monsters = self._get_default_monsters()
        self.sects = self._get_default_sects()
        self.bosses = self._get_default_bosses()
    
    def _get_default_level_config(self) -> List[Dict]:
        """获取默认境界配置"""
        # 由于配置文件存在，此方法应不会被调用，返回空列表
        return []
    
    def _get_default_items(self) -> Dict[str, Dict]:
        """获取默认物品配置"""
        # 由于配置文件存在，此方法应不会被调用，返回空字典
        return {}
    
    def _get_default_monsters(self) -> Dict[str, Dict]:
        """获取默认怪物配置"""
        # 由于配置文件存在，此方法应不会被调用，返回空字典
        return {}

    def _get_default_bosses(self) -> Dict[str, Dict]:
        """获取默认Boss配置"""
        # 由于配置文件存在，此方法应不会被调用，返回空字典
        return {}