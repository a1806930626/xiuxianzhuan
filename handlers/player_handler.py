import random
import asyncio
from typing import Dict, List, Optional
from astrbot.api.event import AstrMessageEvent
from ..models import Player
from ..data.data_manager import DataBase
from ..core.config_manager import ConfigManager


class PlayerHandler:
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_start_xiuxian(self, event: AstrMessageEvent):
        """处理开始修仙命令，创建新玩家并分配灵根"""
        user_id = str(event.get_author_id())
        existing_player = await self.db.get_player_by_id(user_id)
        
        if existing_player:
            yield "您已经注册过修仙了，无需重复注册。"
            yield f"当前境界: {existing_player.get_level(self.config_manager.level_config)['name']}\n当前灵气: {existing_player.spirit}"
            return
        
        # 随机分配灵根
        spiritual_roots = [
            ("天灵根", 0.02),      # 2% 概率
            ("变异灵根", 0.03),    # 3% 概率
            ("上品灵根", 0.08),    # 8% 概率
            ("中品灵根", 0.15),    # 15% 概率
            ("下品灵根", 0.35),    # 35% 概率
            ("伪灵根", 0.37)       # 37% 概率
        ]
        
        # 根据概率随机选择灵根
        rand = random.random()
        cumulative = 0
        selected_root = "未知"
        for root, probability in spiritual_roots:
            cumulative += probability
            if rand <= cumulative:
                selected_root = root
                break
        
        # 创建新玩家
        from ..models import Player
        import time
        from datetime import datetime
        
        new_player = Player(
            user_id=user_id,
            name=event.get_author_name() or f"修仙者{user_id[-4:]}",
            level_index=0,  # 初始境界（练气一层）
            spiritual_root=selected_root,
            max_hp=100,
            current_hp=100,
            attack=10,
            defense=5,
            speed=0,
            spirit=5,  # 初始灵气
            spirit_stone=100,  # 初始灵石
            create_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 保存新玩家
        await self.db.create_player(new_player)
        
        yield f"恭喜您踏上修仙之路！\n您的灵根为：{selected_root}\n当前境界：{new_player.get_level(self.config_manager.level_config)['name']}\n\n修仙之路漫漫，祝您早日得道！"

    async def handle_player_info(self, event: AstrMessageEvent):
        """处理查看玩家信息命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        level_config = self.config_manager.level_config
        current_level = player.get_level(level_config)
        level_name = current_level["name"]
        
        # 获取玩家装备信息
        equipment_info = []
        for pos, item_id in player.equipment_ids.items():
            if item_id:
                item_data = await self.db.get_item_by_id(item_id)
                if item_data:
                    equipment_info.append(f"{pos}:{item_data['name']}")
        
        equipment_str = "、".join(equipment_info) if equipment_info else "无"
        
        # 获取玩家功法信息
        gongfas = await self.db.get_gongfas_by_ids(player.gongfa_ids)
        gongfa_names = [g['name'] for g in gongfas] if gongfas else []
        gongfa_str = "、".join(gongfa_names) if gongfa_names else "无"
        
        yield f"【玩家信息】\n道号: {player.name}\n灵根: {player.spiritual_root}\n境界: {level_name}\n生命值: {player.current_hp}/{player.max_hp}\n攻击力: {player.attack}\n防御力: {player.defense}\n速度: {player.speed}\n灵气: {player.spirit}\n灵石: {player.spirit_stone}\n装备: {equipment_str}\n功法: {gongfa_str}"

    async def handle_sign_in(self, event: AstrMessageEvent):
        """处理签到命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        # 检查今天是否已签到
        if player.last_sign_in == today:
            yield "您今天已经签到过了，明天再来吧！"
            return
        
        # 计算签到奖励
        sign_in_rewards = [
            {"spirit_stone": 10, "spirit": 2},
            {"spirit_stone": 20, "spirit": 4},
            {"spirit_stone": 30, "spirit": 6},
            {"spirit_stone": 40, "spirit": 8},
            {"spirit_stone": 50, "spirit": 10},
            {"spirit_stone": 60, "spirit": 12},
            {"spirit_stone": 100, "spirit": 20}  # 第七天奖励更多
        ]
        
        # 计算连续签到天数（简单实现，实际可能需要更复杂的逻辑）
        day_index = (len(player.last_sign_in) // 10) % 7 if player.last_sign_in else 0  # 简化版本
        reward = sign_in_rewards[day_index % len(sign_in_rewards)]
        
        # 更新玩家数据
        player.spirit_stone += reward["spirit_stone"]
        player.spirit += reward["spirit"]
        player.last_sign_in = today
        player.update_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        await self.db.update_player(player)
        
        yield f"签到成功！\n获得奖励：{reward['spirit_stone']}灵石，{reward['spirit']}灵气\n累计签到：1天\n当前灵石：{player.spirit_stone}\n当前灵气：{player.spirit}"

    async def handle_meditate(self, event: AstrMessageEvent):
        """处理闭关命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 闭关获取灵气奖励（随机范围）
        base_spirit_gain = random.randint(10, 30)  # 基础灵气获取
        
        # 根据玩家当前境界调整获取量
        level_config = self.config_manager.level_config
        current_level = player.get_level(level_config)
        level_name = current_level["name"]
        
        # 不同境界获取灵气的倍率
        if "练气" in level_name:
            multiplier = 1.0
        elif "筑基" in level_name:
            multiplier = 1.2
        elif "金丹" in level_name:
            multiplier = 1.5
        elif "元婴" in level_name:
            multiplier = 1.8
        elif "化神" in level_name:
            multiplier = 2.2
        elif "炼虚" in level_name:
            multiplier = 2.5
        elif "合体" in level_name:
            multiplier = 2.8
        elif "大乘" in level_name:
            multiplier = 3.0
        else:
            multiplier = 1.0
        
        # 获取玩家装备和功法信息
        items = {}
        for pos, item_id in player.equipment_ids.items():
            if item_id:
                item_data = await self.db.get_item_by_id(item_id)
                if item_data:
                    items[item_id] = item_data
        
        gongfas = await self.db.get_gongfas_by_ids(player.gongfa_ids)
        
        # 计算功法加成（灵气获取加成）
        gongfa_spirit_bonus = 0
        if gongfas:
            for gongfa in gongfas:
                gongfa_spirit_bonus += gongfa.get("cultivation_speed_bonus", 0) * 100  # 功法有cultivation_speed_bonus属性，转换为百分比
        
        # 计算装备加成（灵气获取加成）
        equipment_spirit_bonus = 0
        for item_id, item_data in items.items():
            # 装备的spirit属性是数值加成，转换为百分比加成（假设每10点spirit属性提供1%灵气获取加成）
            equipment_spirit_value = item_data.get("spirit", 0)
            equipment_spirit_bonus += equipment_spirit_value * 0.1  # 每10点spirit提供1%加成
        
        # 计算灵根加成（根据灵根类型提供不同加成）
        spiritual_root_bonus = 0
        if player.spiritual_root == "天灵根":
            spiritual_root_bonus = 0.3  # 天灵根最高加成
        elif player.spiritual_root == "变异灵根":
            spiritual_root_bonus = 0.25
        elif player.spiritual_root == "上品灵根":
            spiritual_root_bonus = 0.2
        elif player.spiritual_root == "中品灵根":
            spiritual_root_bonus = 0.15
        elif player.spiritual_root == "下品灵根":
            spiritual_root_bonus = 0.1
        elif player.spiritual_root == "伪灵根":
            spiritual_root_bonus = 0.05
        else:
            spiritual_root_bonus = 0.0  # 未知灵根无加成
        
        # 计算总加成倍率
        total_multiplier = multiplier * (1 + gongfa_spirit_bonus/100 + equipment_spirit_bonus/100) * (1 + spiritual_root_bonus)
        
        spirit_gained = int(base_spirit_gain * total_multiplier)
        
        # 更新玩家灵气
        player.spirit += spirit_gained
        await self.db.update_player(player)
        
        # 准备输出信息
        gongfa_bonus_text = f"功法加成: {gongfa_spirit_bonus:.1f}%"
        equipment_bonus_text = f"装备加成: {equipment_spirit_bonus:.1f}%"
        root_bonus_text = f"灵根加成: {spiritual_root_bonus*100:.0f}%"
        
        yield f"闭关修炼结束！\n当前境界: {level_name}\n{gongfa_bonus_text}\n{equipment_bonus_text}\n{root_bonus_text}\n获得灵气: {spirit_gained}\n总灵气: {player.spirit}\n\n静心凝神，感悟天地灵气，修为有所精进。"
        
        # 随机事件（可选，增加趣味性）
        if random.random() < 0.1:  # 10%几率触发特殊事件
            special_events = [
                "在闭关中感悟到一丝天道玄机，灵气运转更加顺畅。",
                "闭关时偶得灵光一闪，对功法有了新的理解。",
                "冥冥之中似有仙缘相助，修为进展神速。",
                "闭关期间心境提升，对修仙之路有了更深的领悟。"
            ]
            yield f"【特殊感悟】{random.choice(special_events)}"