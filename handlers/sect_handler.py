# handlers/sect_handler.py

from astrbot.api.event import AstrMessageEvent
from astrbot.api import AstrBotConfig
from ..data.data_manager import DataBase
from ..core.sect_manager import SectManager
from ..models import Player


class SectHandler:
    def __init__(self, db: DataBase, config: AstrBotConfig):
        self.db = db
        self.config = config
        self.sect_manager = SectManager(db, config)

    async def handle_sect(self, event: AstrMessageEvent):
        """处理宗门指令"""
        user_id = event.get_user_id()
        
        # 获取玩家信息
        player = await self.db.get_player(user_id)
        if not player:
            yield "道友尚未踏入修仙之路，请先「我要修仙」。"
            return

        if player.sect_id is None:
            yield "道友目前尚未加入任何宗门。"
            yield "可使用「加入宗门 [宗门名称]」加入宗门，或「创建宗门 [宗门名称]」自立门户。"
            return

        # 获取宗门详细信息
        sect = await self.db.get_sect_by_id(player.sect_id)
        if not sect:
            yield "未能获取宗门信息，请稍后再试。"
            return

        # 获取宗门成员列表
        members = await self.db.get_sect_members(player.sect_id)
        
        # 构建宗门信息
        sect_info = f"""
【{sect['name']}】
宗门ID: {sect['id']}
宗主: {sect.get('master_nickname', '待定')}
宗门等级: {sect['level']}
宗门经验: {sect['experience']}
成员数量: {len(members)}
成员列表: {', '.join([member['name'] for member in members[:10]])}{'...' if len(members) > 10 else ''}
        """.strip()
        
        yield sect_info

    async def handle_join_sect(self, event: AstrMessageEvent):
        """处理加入宗门指令"""
        user_id = event.get_user_id()
        message = event.get_plain_text()
        
        # 获取玩家信息
        player = await self.db.get_player(user_id)
        if not player:
            yield "道友尚未踏入修仙之路，请先「我要修仙」。"
            return

        # 解析宗门名称
        parts = message.split(" ", 1)
        if len(parts) < 2:
            yield "指令格式错误，请使用「加入宗门 [宗门名称]」。"
            return

        sect_name = parts[1].strip()
        if not sect_name:
            yield "请输入有效的宗门名称。"
            return

        # 使用sect_manager处理加入宗门逻辑
        success, msg, updated_player = await self.sect_manager.handle_join_sect(player, sect_name)
        
        if success and updated_player:
            # 更新玩家信息
            await self.db.update_player(updated_player)
            yield msg
        else:
            yield msg

    async def handle_create_sect(self, event: AstrMessageEvent):
        """处理创建宗门指令"""
        user_id = event.get_user_id()
        message = event.get_plain_text()
        
        # 获取玩家信息
        player = await self.db.get_player(user_id)
        if not player:
            yield "道友尚未踏入修仙之路，请先「我要修仙」。"
            return

        # 解析宗门名称
        parts = message.split(" ", 1)
        if len(parts) < 2:
            yield "指令格式错误，请使用「创建宗门 [宗门名称]」。"
            return

        sect_name = parts[1].strip()
        if not sect_name:
            yield "请输入有效的宗门名称。"
            return

        # 使用sect_manager处理创建宗门逻辑
        success, msg, updated_player = await self.sect_manager.handle_create_sect(player, sect_name)
        
        if success and updated_player:
            # 更新玩家信息
            await self.db.update_player(updated_player)
            yield msg
        else:
            yield msg

    async def handle_leave_sect(self, event: AstrMessageEvent):
        """处理离开宗门指令"""
        user_id = event.get_user_id()
        
        # 获取玩家信息
        player = await self.db.get_player(user_id)
        if not player:
            yield "道友尚未踏入修仙之路，请先「我要修仙」。"
            return

        # 使用sect_manager处理离开宗门逻辑
        success, msg, updated_player = await self.sect_manager.handle_leave_sect(player)
        
        if success and updated_player:
            # 更新玩家信息
            await self.db.update_player(updated_player)
            yield msg
        else:
            yield msg