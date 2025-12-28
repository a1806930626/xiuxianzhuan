from astrbot.api.event import AstrMessageEvent
from ..models import Player
from ..data.data_manager import DataBase
from ..core.config_manager import ConfigManager
from typing import Dict, List, Optional
import asyncio
import random


class RealmHandler:
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_breakthrough(self, event: AstrMessageEvent):
        """处理境界突破"""
        user_id = str(event.get_author_id())
        
        player = await self.db.get_player_by_id(user_id)
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return

        # 获取当前境界信息
        current_level = player.get_level(self.config_manager.level_config)
        current_level_name = current_level["name"]
        current_spirit_threshold = current_level["spirit"]
        
        # 检查是否已经是最高境界
        if player.level_index >= len(self.config_manager.level_config) - 1:
            yield f"您已经达到了最高境界 {current_level_name}，无法继续突破。"
            return

        # 获取下一个境界信息
        next_level_index = player.level_index + 1
        if next_level_index < len(self.config_manager.level_config):
            next_level = self.config_manager.level_config[next_level_index]
            next_level_name = next_level["name"]
            next_spirit_threshold = next_level["spirit"]
        else:
            yield "您已经达到了最高境界，无法继续突破。"
            return

        # 检查玩家的spirit值是否满足突破条件
        if player.spirit < next_spirit_threshold:
            yield f"突破失败！\n当前境界: {current_level_name}\n下个境界: {next_level_name}\n所需灵气: {next_spirit_threshold}\n当前灵气: {player.spirit}\n\n您的灵气不足，无法突破到下一个境界。"
            return

        # 执行突破逻辑
        success_rate = self._calculate_breakthrough_success_rate(player, next_level_index)
        
        if random.random() <= success_rate:
            # 突破成功
            player.level_index = next_level_index
            # 扣除突破所需的灵气
            player.spirit -= next_spirit_threshold
            
            # 增加基础属性
            player.max_hp = int(player.max_hp * 1.2)  # 基础生命值增加20%
            player.attack = int(player.attack * 1.2)  # 基础攻击力增加20%
            player.defense = int(player.defense * 1.2)  # 基础防御力增加20%
            player.speed = int(player.speed * 1.2)  # 基础速度增加20%
            
            # 更新玩家信息
            await self.db.update_player(player)
            
            yield f"突破成功！\n恭喜您突破到 {next_level_name}！\n当前境界: {next_level_name}\n当前灵气: {player.spirit}\n\n基础属性已提升20%！"
        else:
            # 判断是否为中境界（炼虚期开始，即索引22开始）
            is_middle_realm = next_level_index >= 22  # 炼虚初期是索引22
            
            if is_middle_realm:
                 # 中境界突破失败，触发天道惩罚
                 punishment_chance = 0.3  # 30%的几率触发天道惩罚
                 if random.random() <= punishment_chance:
                     # 天道惩罚生效，境界跌落
                     original_level_index = player.level_index  # 保存当前境界索引
                     player.level_index = max(0, player.level_index - 1)  # 回退一个境界
                     
                     # 恢复部分灵气
                     player.spirit = max(0, int(player.spirit * 0.5))  # 恢复一半灵气
                     
                     # 更新玩家信息
                     await self.db.update_player(player)
                     
                     current_level = player.get_level(self.config_manager.level_config)
                     current_level_name = current_level["name"]
                     
                     yield f"突破失败！天道轮回，您被降回 {current_level_name}！\n天道惩罚降临，境界跌落，灵气减半。\n当前境界: {current_level_name}\n当前灵气: {player.spirit}\n\n继续修炼，再攀仙途高峰！"
                 else:
                     # 天道惩罚未触发，正常惩罚
                     spirit_loss_percentage = 0.2  # 损失20%的灵气（中境界失败惩罚更重）
                     spirit_lost = int(player.spirit * spirit_loss_percentage)
                     player.spirit = max(0, player.spirit - spirit_lost)  # 确保灵气不会变成负数
                     
                     # 更新玩家信息
                     await self.db.update_player(player)
                     
                     yield f"突破失败！\n当前境界: {current_level_name}\n下个境界: {next_level_name}\n突破成功率: {success_rate:.1%}\n损失灵气: {spirit_lost}\n剩余灵气: {player.spirit}\n\n继续修炼积累灵气，下次尝试突破吧！"
            else:
                # 非中境界突破失败，正常惩罚
                spirit_loss_percentage = 0.1  # 损失10%的灵气
                spirit_lost = int(player.spirit * spirit_loss_percentage)
                player.spirit = max(0, player.spirit - spirit_lost)  # 确保灵气不会变成负数
                
                # 更新玩家信息
                await self.db.update_player(player)
                
                yield f"突破失败！\n当前境界: {current_level_name}\n下个境界: {next_level_name}\n突破成功率: {success_rate:.1%}\n损失灵气: {spirit_lost}\n剩余灵气: {player.spirit}\n\n继续修炼积累灵气，下次尝试突破吧！"

    def _calculate_breakthrough_success_rate(self, player: Player, next_level_index: int) -> float:
        """计算突破成功率"""
        # 基础成功率
        base_success_rate = 0.5  # 50%基础成功率
        
        # 根据境界等级调整成功率，越往后成功率越低
        level_multiplier = max(0.1, 1.0 - (next_level_index * 0.15))  # 更陡峭的下降曲线
        
        # 根据玩家当前灵气值调整成功率，灵气越多成功率越高
        # 灵气值越高，突破成功率加成越高，最多增加50%成功率
        spirit_multiplier = 1 + min(0.5, (player.spirit / 500) * 0.2)  # 每500点灵力增加20%成功率，最多增加50%
        
        success_rate = base_success_rate * level_multiplier * spirit_multiplier
        
        return min(0.95, success_rate)  # 最大成功率不超过95%