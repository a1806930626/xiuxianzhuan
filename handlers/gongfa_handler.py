from astrbot.api.event import AstrMessageEvent
from ..data.data_manager import DataBase
from ..core.config_manager import ConfigManager
from typing import Dict, Any
import random


class GongfaHandler:
    """功法相关命令处理"""
    
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_gongfa(self, event: AstrMessageEvent):
        """处理功法命令，查看玩家已学习的功法"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取玩家已学习的功法
        gongfa_ids = player.gongfa_ids
        if not gongfa_ids:
            yield "您还没有学习任何功法。"
            return
        
        gongfas = await self.db.get_gongfas_by_ids(gongfa_ids)
        if not gongfas:
            yield "您还没有学习任何功法。"
            return
        
        gongfa_info = "【您的功法】\n"
        for gongfa in gongfas:
            gongfa_info += f"功法名称: {gongfa.get('name', '未知功法')}\n"
            gongfa_info += f"功法类型: {gongfa.get('type', '未知类型')}\n"
            gongfa_info += f"修炼速度加成: {gongfa.get('cultivation_speed_bonus', 0)*100:.1f}%\n"
            gongfa_info += f"属性加成: 攻击+{gongfa.get('attack_bonus', 0)}, 防御+{gongfa.get('defense_bonus', 0)}, 生命+{gongfa.get('hp_bonus', 0)}\n"
            gongfa_info += f"描述: {gongfa.get('description', '暂无描述')}\n\n"
        
        yield gongfa_info

    async def handle_learn_gongfa(self, event: AstrMessageEvent):
        """处理学习功法命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取命令参数
        message = event.get_content().strip()
        parts = message.split(" ", 1)
        
        if len(parts) < 2:
            yield "请指定要学习的功法名称，格式：学习功法 [功法名称]"
            return
        
        gongfa_name = parts[1].strip()
        
        # 从配置中获取所有功法
        all_gongfas = self.config_manager.items  # 功法信息可能存储在items中
        
        # 查找指定功法
        target_gongfa = None
        target_gongfa_id = None
        for item_id, item_data in all_gongfas.items():
            if item_data.get('name') == gongfa_name and item_data.get('type') == 'gongfa':
                target_gongfa = item_data
                target_gongfa_id = item_id
                break
        
        if not target_gongfa:
            # 如果在items中没找到，尝试从其他可能的配置中查找
            yield f"未找到功法：{gongfa_name}，请检查功法名称是否正确。"
            return
        
        # 检查玩家是否已经学习了该功法
        if target_gongfa_id in player.gongfa_ids:
            yield f"您已经学会了功法：{gongfa_name}，无需重复学习。"
            return
        
        # 检查玩家的境界是否满足学习条件
        required_realm_name = target_gongfa.get('required_realm', "练气一层")
        realm_config = self.config_manager.realm_config
        
        # 获取玩家当前境界
        player_realm = player.get_realm(realm_config)
        player_realm_name = player_realm["name"]
        
        # 查找要求境界在配置中的索引
        required_realm_index = -1
        for i, realm in enumerate(realm_config):
            if realm["name"] == required_realm_name:
                required_realm_index = i
                break
        
        # 如果找不到要求境界，默认为练气一层
        if required_realm_index == -1:
            required_realm_index = 0
            required_realm_name = "练气一层"
        
        if player.realm_index < required_realm_index:
            yield f"您的境界不足以学习此功法！\n需要境界：{required_realm_name}\n当前境界：{player_realm_name}"
            return
        
        # 检查玩家是否拥有该功法秘籍（在背包中）
        inventory = await self.db.get_player_inventory(user_id)
        has_gongfa_book = False
        gongfa_book_id = None
        
        for item_id, count in inventory.items():
            item_data = await self.db.get_item_by_id(item_id)
            if item_data and item_data.get('name') == gongfa_name and item_data.get('type') == 'gongfa_book':
                has_gongfa_book = True
                gongfa_book_id = item_id
                break
        
        if not has_gongfa_book:
            yield f"您没有功法秘籍《{gongfa_name}》，无法学习该功法。"
            return
        
        # 学习功法成功
        player.gongfa_ids.append(target_gongfa_id)
        
        # 从背包中移除功法秘籍
        if gongfa_book_id:
            await self.db.remove_item_from_inventory(user_id, gongfa_book_id, 1)
        
        # 更新玩家信息
        await self.db.update_player(player)
        
        yield f"恭喜您成功学习功法《{gongfa_name}》！\n该功法将为您提供永久属性加成。"