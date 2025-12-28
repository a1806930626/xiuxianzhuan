from astrbot.api.event import AstrMessageEvent
from ..data.data_manager import DataBase
from ..core.config_manager import ConfigManager
from typing import Dict, Any


class ShopHandler:
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_shop(self, event: AstrMessageEvent):
        """处理坊市命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取商品列表
        items = await self.db.get_all_items()
        
        shop_message = "【坊市】\n"
        shop_message += "欢迎来到坊市！\n\n"
        shop_message += "商品列表：\n"
        
        for item in items:
            shop_message += f"{item.name} - {item.description} - 价格: {item.price}灵石\n"
        
        shop_message += "\n使用'购买 [商品名称]'可购买商品。"
        yield shop_message

    async def handle_backpack(self, event: AstrMessageEvent):
        """处理背包命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取玩家背包
        inventory = await self.db.get_player_inventory(user_id)
        
        if not inventory or len(inventory) == 0:
            yield "您的背包是空的。"
            return
        
        backpack_message = "【我的背包】\n"
        backpack_message += "您当前拥有的物品：\n"
        
        for item_id, count in inventory.items():
            item_data = await self.db.get_item_by_id(item_id)
            if item_data:
                backpack_message += f"{item_data['name']} x{count}\n"
            else:
                backpack_message += f"{item_id} x{count}\n"
        
        yield backpack_message

    async def handle_buy(self, event: AstrMessageEvent):
        """处理购买命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取命令参数
        message = event.get_event_message().strip()
        parts = message.split(" ", 1)
        
        if len(parts) < 2:
            yield "请指定要购买的商品ID，格式：购买 [商品ID] 或 购买 [商品ID] [数量]"
            return
        
        # 解析参数 - 支持购买指定数量的物品
        params = parts[1].strip().split(" ")
        item_id = params[0]
        quantity = 1  # 默认数量为1
        
        if len(params) > 1:
            try:
                quantity = int(params[1])
                if quantity <= 0:
                    yield "购买数量必须大于0"
                    return
            except ValueError:
                yield "数量必须是数字"
                return
        
        # 通过ID查找商品
        target_item = await self.db.get_item_by_id(item_id)
        
        if not target_item:
            yield f"未找到商品ID：{item_id}"
            return
        
        # 检查玩家灵石是否足够
        total_price = target_item['price'] * quantity
        if player.spirit_stone < total_price:
            yield f"您的灵石不足，需要{total_price}灵石，您当前有{player.spirit_stone}灵石。"
            return
        
        # 扣除灵石并添加物品到背包
        player.spirit_stone -= total_price
        await self.db.add_item_to_inventory(user_id, item_id, quantity)
        await self.db.update_player(player)
        
        yield f"购买成功！花费{total_price}灵石购买了{quantity}个{target_item['name']}。"

    async def handle_use_item(self, event: AstrMessageEvent):
        """处理使用物品命令"""
        user_id = str(event.get_author_id())
        player = await self.db.get_player_by_id(user_id)
        
        if not player:
            yield "您还没有开始修仙，请先输入'我要修仙'注册。"
            return
        
        # 获取命令参数
        message = event.get_event_message().strip()
        parts = message.split(" ", 1)
        
        if len(parts) < 2:
            yield "请指定要使用的物品ID，格式：使用 [物品ID] 或 使用 [物品ID] [数量]"
            return
        
        # 解析参数 - 支持使用指定数量的物品
        params = parts[1].strip().split(" ")
        item_id = params[0]
        quantity = 1  # 默认数量为1
        
        if len(params) > 1:
            try:
                quantity = int(params[1])
                if quantity <= 0:
                    yield "使用数量必须大于0"
                    return
            except ValueError:
                yield "数量必须是数字"
                return
        
        # 检查背包中是否有该物品ID
        inventory = await self.db.get_player_inventory(user_id)
        if item_id not in inventory or inventory[item_id] < quantity:
            # 为了更好的用户体验，尝试通过名称查找物品
            target_item_id = None
            target_item = None
            item_name = item_id  # 将输入当作名称处理
            
            for inv_item_id, count in inventory.items():
                item = await self.db.get_item_by_id(inv_item_id)
                if item and item["name"] == item_name and count >= quantity:
                    target_item_id = inv_item_id
                    target_item = item
                    break
            
            if not target_item:
                yield f"背包中没有足够的物品：{item_id}"
                return
            else:
                # 找到了匹配的物品名称，更新item_id
                item_id = target_item_id
        else:
            # 通过ID找到了物品，获取物品详情
            target_item = await self.db.get_item_by_id(item_id)
            if not target_item:
                yield f"无效的物品ID：{item_id}"
                return
        
        # 首先尝试从 danyao 表获取 elixir 效果
        item_name = target_item["name"]
        danyao_data = await self.db.get_danyao_by_name(item_name)
        effects = {}
        
        if danyao_data:
            # 如果是 elixir，从 danyao 表获取效果
            effects = danyao_data.get("effect", {})
        else:
            # 如果不是 elixir，从 items 表获取效果（保持向后兼容）
            import json
            if isinstance(target_item.get("effect"), str):
                try:
                    effects = json.loads(target_item["effect"])
                except:
                    effects = {}
            else:
                effects = target_item.get("effects", {}) or target_item.get("effect", {})
        
        # 处理不同类型的物品效果
        effect_messages = []
        for effect_type, value in effects.items():
            if effect_type == "hp":
                player.current_hp = min(player.max_hp, player.current_hp + value * quantity)
                effect_messages.append(f"恢复{value * quantity}点生命值")
            elif effect_type == "spirit":
                player.spirit = max(0, player.spirit + value * quantity)
                effect_messages.append(f"恢复{value * quantity}点灵力")
            elif effect_type == "attack":
                # 装备类物品需要特殊处理，这里暂时只处理消耗品
                effect_messages.append(f"增加{value * quantity}点攻击力（临时效果）")
            elif effect_type == "defense":
                effect_messages.append(f"增加{value * quantity}点防御力（临时效果）")
            elif effect_type == "max_hp":
                player.max_hp += value * quantity
                player.current_hp = min(player.current_hp + value * quantity, player.max_hp)
                effect_messages.append(f"永久增加{value * quantity}点最大生命值")
            elif effect_type == "max_spirit":
                player.max_spirit += value * quantity
                player.spirit = min(player.spirit + value * quantity, player.max_spirit)
                effect_messages.append(f"永久增加{value * quantity}点最大灵力")
            elif effect_type == "exp":
                player.exp += value * quantity
                effect_messages.append(f"获得{value * quantity}点经验值")
        
        # 从背包中移除使用过的物品
        await self.db.remove_item_from_inventory(user_id, item_id, quantity)
        
        # 更新玩家信息
        await self.db.update_player(player)
        
        if effect_messages:
            yield f"使用成功！{quantity}个{item_name}，{', '.join(effect_messages)}。"
        else:
            yield f"使用了{quantity}个{item_name}，但没有产生明显效果。"