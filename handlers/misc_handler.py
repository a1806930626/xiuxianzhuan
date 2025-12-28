from astrbot.api.event import AstrMessageEvent
from ..data.data_manager import DataBase
from ..core.config_manager import ConfigManager


class MiscHandler:
    """杂项命令处理"""
    
    def __init__(self, db: DataBase, config_manager: ConfigManager):
        self.db = db
        self.config_manager = config_manager

    async def handle_help(self, event: AstrMessageEvent):
        """处理帮助命令"""
        help_text = """
【修仙转帮助】
        
【玩家相关】
- 我要修仙：开始修仙之路，创建角色
- 我的信息：查看角色详细信息
- 签到：每日签到获得奖励
- 闭关：闭关修炼获取灵气

【坊市相关】
- 坊市：查看可购买商品
- 我的背包：查看背包物品
- 购买 [商品名称]：购买指定商品
- 使用 [物品名称]：使用背包中的物品

【战斗相关】
- 挑战：挑战随机怪物
- 竞技场：与其他玩家对战

【境界相关】
- 突破：尝试突破到下一个境界

【宗门相关】
- 宗门：查看宗门信息
- 加入宗门 [宗门名称]：加入指定宗门

【装备相关】
- 装备：查看当前装备
- 穿戴 [装备ID]：穿戴指定装备

【功法相关】
- 功法：查看已学功法
- 学习功法 [功法名称]：学习指定功法

祝您修仙愉快，早日得道成仙！
        """
        yield help_text.strip()