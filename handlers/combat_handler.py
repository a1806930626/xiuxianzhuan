import random
import asyncio
from typing import Dict, List, Optional
from astrbot.api.event import AstrMessageEvent
from ..models import Player, Monster, CombatLog
from ..data.data_manager import DataBase
from ..core.config_manager import ConfigManager


class CombatHandler:
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_challenge(self, event: AstrMessageEvent):
        """处理挑战怪物命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取怪物配置
        monsters = self.config_manager.monsters
        if not monsters:
            yield "暂无可用怪物。"
            return
        
        # 随机选择一个怪物
        monster_id = random.choice(list(monsters.keys()))
        monster_data = monsters[monster_id]
        
        # 获取玩家装备和功法
        items = {}
        equipment_ids = player.equipment_ids
        for pos, item_id in equipment_ids.items():
            if item_id:
                item_data = await self.db.get_item_by_id(item_id)
                if item_data:
                    items[item_id] = item_data
        
        gongfas = await self.db.get_gongfas_by_ids(player.gongfa_ids)
        
        # 获取玩家战斗属性
        player_stats = player.get_combat_stats(items, gongfas)
        
        # 根据玩家属性计算怪物属性（为玩家属性的50%）
        monster_max_hp = int(player_stats["hp"] * 0.5)
        monster_attack = int(player_stats["attack"] * 0.5)
        monster_defense = int(player_stats["defense"] * 0.5)
        monster_speed = int(player_stats["speed"] * 0.5)
        
        # 使用配置中的基础值作为最小值，避免玩家属性太低导致怪物属性为0
        monster_max_hp = max(monster_data["max_hp_base"], monster_max_hp)
        monster_attack = max(monster_data["attack_base"], monster_attack)
        monster_defense = max(monster_data["defense_base"], monster_defense)
        monster_speed = max(monster_data["speed_base"], monster_speed)
        
        monster = Monster(
            monster_id=monster_id,
            name=monster_data["name"],
            max_hp=monster_max_hp,
            attack=monster_attack,
            defense=monster_defense,
            speed=monster_speed,
            spirit_stone=monster_data["spirit_stone"],
            drop_items=monster_data.get("drop_items", [])
        )
        
        # 开始战斗
        yield f"开始挑战 {monster.name}！"
        yield f"战斗开始！\n玩家: HP {player.current_hp}/{player_stats['hp']}\n怪物: HP {monster.max_hp}/{monster.max_hp}"
        
        # 战斗循环
        player_hp = player.current_hp
        monster_hp = monster.max_hp
        
        # 获取玩家装备的物品信息
        all_items = {}
        for pos, item_id in player.equipment_ids.items():
            if item_id:
                item_data = await self.db.get_item_by_id(item_id)
                if item_data:
                    all_items[item_id] = item_data
        
        player_gongfas = await self.db.get_gongfas_by_ids(player.gongfa_ids)
        player_combat_stats = player.get_combat_stats(all_items, player_gongfas)
        
        # 比较玩家和怪物速度，速度快的先出手
        if player_combat_stats["speed"] >= monster.speed:
            player_first = True
            yield f"速度对比：你的速度({player_combat_stats['speed']}) vs {monster.name}的速度({monster.speed})，你先出手！"
        else:
            player_first = False
            yield f"速度对比：你的速度({player_combat_stats['speed']}) vs {monster.name}的速度({monster.speed})，{monster.name}先出手！"
        
        round_num = 1
        while player_hp > 0 and monster_hp > 0:
            yield f"\n第{round_num}回合："
            
            if player_first:
                # 玩家先攻击
                player_damage = max(1, player_combat_stats["attack"] - monster.defense)
                monster_hp -= player_damage
                yield f"你对{monster.name}造成了{player_damage}点伤害！"
                
                if monster_hp <= 0:
                    yield f"{monster.name}被击败了！"
                    break
                
                # 怪物后攻击
                monster_damage = max(1, monster.attack - player_combat_stats["defense"])
                player_hp -= monster_damage
                yield f"{monster.name}对你造成了{monster_damage}点伤害！"
            else:
                # 怪物先攻击
                monster_damage = max(1, monster.attack - player_combat_stats["defense"])
                player_hp -= monster_damage
                yield f"{monster.name}对你造成了{monster_damage}点伤害！"
                
                if player_hp <= 0:
                    yield "你被击败了！"
                    break
                
                # 玩家后攻击
                player_damage = max(1, player_combat_stats["attack"] - monster.defense)
                monster_hp -= player_damage
                yield f"你对{monster.name}造成了{player_damage}点伤害！"
                
                if monster_hp <= 0:
                    yield f"{monster.name}被击败了！"
                    break
            
            if player_hp <= 0:
                yield "你被击败了！"
                break
            
            round_num += 1
            await asyncio.sleep(0.5)  # 战斗延迟
        
        # 战斗结果处理
        if player_hp > 0:
            # 玩家胜利
            result = "win"
            spirit_stone_gained = monster.spirit_stone
            
            # 随机掉落物品
            drop_items = []
            for drop_item in monster.drop_items:
                if random.random() < drop_item["probability"]:
                    drop_items.append(drop_item["item_id"])
                    # 添加物品到背包
                    await self.db.add_item_to_inventory(user_id, drop_item["item_id"])
            
            # 战斗胜利获得灵气奖励（用于突破）
            spirit_gained = max(1, monster.max_hp // 10)  # 根据怪物血量给予灵气奖励
            
            # 更新玩家灵石和灵气
            player.spirit_stone += spirit_stone_gained
            player.spirit += spirit_gained
            player.current_hp = player_hp  # 更新当前血量
            await self.db.update_player(player)
            
            yield f"\n战斗胜利！获得{spirit_stone_gained}灵石，获得{spirit_gained}灵气！"
            
            if drop_items:
                item_names = []
                for item_id in drop_items:
                    item_data = await self.db.get_item_by_id(item_id)
                    if item_data:
                        item_names.append(item_data.get("name", item_id))
                yield f"获得物品：{', '.join(item_names)}"
            
            # 记录战斗日志
            combat_log = CombatLog(
                log_id=f"combat_{user_id}_{int(asyncio.get_event_loop().time())}",
                attacker_id=user_id,
                defender_id=monster.monster_id,
                result=result,
                damage=monster.max_hp - monster_hp,
                spirit_stone_gained=spirit_stone_gained,
                timestamp=asyncio.get_event_loop().time(),
                drop_items=drop_items
            )
            await self.db.add_combat_log(combat_log)
        else:
            # 玩家失败
            result = "lose"
            yield f"\n战斗失败！"
            
            # 记录战斗日志
            combat_log = CombatLog(
                log_id=f"combat_{user_id}_{int(asyncio.get_event_loop().time())}",
                attacker_id=user_id,
                defender_id=monster.monster_id,
                result=result,
                damage=player.max_hp - player_hp,
                spirit_stone_gained=0,
                timestamp=asyncio.get_event_loop().time(),
                drop_items=[]
            )
            await self.db.add_combat_log(combat_log)

    async def handle_arena(self, event: AstrMessageEvent):
        """处理竞技场命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取所有玩家（排除自己）
        all_players = await self.db.get_all_players()
        other_players = [p for p in all_players if p.user_id != user_id and p.level_index <= player.level_index + 2]
        
        if not other_players:
            yield "竞技场暂无合适的对手。"
            return
        
        # 随机选择一个对手
        opponent = random.choice(other_players)
        
        # 获取双方的装备和功法
        player_items = {}
        for pos, item_id in player.equipment_ids.items():
            if item_id:
                item_data = await self.db.get_item_by_id(item_id)
                if item_data:
                    player_items[item_id] = item_data
        
        opponent_items = {}
        for pos, item_id in opponent.equipment_ids.items():
            if item_id:
                item_data = await self.db.get_item_by_id(item_id)
                if item_data:
                    opponent_items[item_id] = item_data
        
        player_gongfas = await self.db.get_gongfas_by_ids(player.gongfa_ids)
        opponent_gongfas = await self.db.get_gongfas_by_ids(opponent.gongfa_ids)
        
        # 获取战斗属性
        player_stats = player.get_combat_stats(player_items, player_gongfas)
        opponent_stats = opponent.get_combat_stats(opponent_items, opponent_gongfas)
        
        yield f"竞技场战斗：你 VS {opponent.name}"
        yield f"战斗开始！\n你的HP: {player.current_hp}/{player_stats['hp']}\n对手HP: {opponent.current_hp}/{opponent_stats['hp']}"
        
        # 战斗循环
        player_hp = player.current_hp
        opponent_hp = opponent.current_hp
        
        # 比较双方速度，速度快的先出手
        if player_stats["speed"] >= opponent_stats["speed"]:
            first_attacker = "player"
            first_stats = player_stats
            second_attacker = "opponent"
            second_stats = opponent_stats
            first_hp = player_hp
            second_hp = opponent_hp
        else:
            first_attacker = "opponent"
            first_stats = opponent_stats
            second_attacker = "player"
            second_stats = player_stats
            first_hp = opponent_hp
            second_hp = player_hp
        
        yield f"速度对比：你的速度({player_stats['speed']}) vs {opponent.name}的速度({opponent_stats['speed']})"
        
        round_num = 1
        while player_hp > 0 and opponent_hp > 0:
            yield f"\n第{round_num}回合："
            
            # 速度快的先攻击
            if first_attacker == "player":
                first_damage = max(1, first_stats["attack"] - second_stats["defense"])
                second_hp -= first_damage
                yield f"你对{opponent.name}造成了{first_damage}点伤害！"
                
                if second_hp <= 0:
                    yield f"{opponent.name}被击败了！"
                    break
            else:
                first_damage = max(1, first_stats["attack"] - second_stats["defense"])
                second_hp -= first_damage
                yield f"{opponent.name}对你造成了{first_damage}点伤害！"
                
                if second_hp <= 0:
                    yield "你被击败了！"
                    break
            
            # 速度慢的后攻击
            if second_attacker == "player":
                second_damage = max(1, second_stats["attack"] - first_stats["defense"])
                first_hp -= second_damage
                yield f"你对{opponent.name}造成了{second_damage}点伤害！"
            else:
                second_damage = max(1, second_stats["attack"] - first_stats["defense"])
                first_hp -= second_damage
                yield f"{opponent.name}对你造成了{second_damage}点伤害！"
            
            if first_hp <= 0:
                if second_attacker == "player":
                    yield "你被击败了！"
                else:
                    yield f"{opponent.name}被击败了！"
                break
            
            # 更新血量
            if player_stats["speed"] >= opponent_stats["speed"]:
                player_hp = first_hp
                opponent_hp = second_hp
            else:
                player_hp = second_hp
                opponent_hp = first_hp
            
            round_num += 1
            await asyncio.sleep(0.5)  # 战斗延迟
        
        # 战斗结果处理
        if player_hp > 0:
            # 玩家胜利
            result = "win"
            spirit_stone_gained = opponent.spirit_stone // 4  # 获得对手部分灵石
            spirit_gained = max(1, opponent.max_hp // 20)  # 根据对手血量给予灵气奖励
            
            # 更新玩家灵石和灵气
            player.spirit_stone += spirit_stone_gained
            player.spirit += spirit_gained
            player.current_hp = player_hp  # 更新当前血量
            await self.db.update_player(player)
            
            yield f"\n竞技场胜利！获得{spirit_stone_gained}灵石，获得{spirit_gained}灵气！"
            
            # 记录战斗日志
            combat_log = CombatLog(
                log_id=f"arena_{user_id}_{int(asyncio.get_event_loop().time())}",
                attacker_id=user_id,
                defender_id=opponent.user_id,
                result=result,
                damage=opponent_stats['hp'] - opponent_hp,
                spirit_stone_gained=spirit_stone_gained,
                timestamp=asyncio.get_event_loop().time(),
                drop_items=[]
            )
            await self.db.add_combat_log(combat_log)
        else:
            # 玩家失败
            result = "lose"
            spirit_stone_lost = player.spirit_stone // 10  # 失去部分灵石
            player.spirit_stone = max(0, player.spirit_stone - spirit_stone_lost)
            player.current_hp = player_hp  # 更新当前血量
            await self.db.update_player(player)
            
            yield f"\n竞技场失败！失去{spirit_stone_lost}灵石。"
            
            # 记录战斗日志
            combat_log = CombatLog(
                log_id=f"arena_{user_id}_{int(asyncio.get_event_loop().time())}",
                attacker_id=user_id,
                defender_id=opponent.user_id,
                result=result,
                damage=player_stats['hp'] - player_hp,
                spirit_stone_gained=-spirit_stone_lost,  # 负数表示失去
                timestamp=asyncio.get_event_loop().time(),
                drop_items=[]
            )
            await self.db.add_combat_log(combat_log)