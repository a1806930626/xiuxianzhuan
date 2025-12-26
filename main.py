import traceback

from astrbot.core import Context, Star, AstrBotConfig
from astrbot.core.message import AstrMessageEvent
from astrbot.utils import register

from .core.config_manager import ConfigManager
from .data.data_manager import DataBase
from .handlers.player_handler import PlayerHandler
from .handlers.shop_handler import ShopHandler
from .handlers.combat_handler import CombatHandler
from .handlers.realm_handler import RealmHandler
from .handlers.sect_handler import SectHandler
from .handlers.equipment_handler import EquipmentHandler
from .handlers.gongfa_handler import GongfaHandler
from .handlers.misc_handler import MiscHandler
from .manager.server import create_app


@register(
    "astrbot_plugin_xiuxianzhuan",
    "oldPeter616",
    "基于astrbot框架的文字修仙游戏",
    "v1.0.0",
    "https://github.com/oldPeter616/astrbot_plugin_xiuxian"
)
class XiuXianZhuangPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context, config)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager(self.get_plugin_dir())
        
        # 初始化数据库
        self.db = DataBase(self.get_plugin_dir())
        
        # 初始化各个处理器
        self.player_handler = PlayerHandler(self.db, self.config_manager)
        self.shop_handler = ShopHandler(self.db, self.config_manager)
        self.combat_handler = CombatHandler(self.db, self.config_manager)
        self.realm_handler = RealmHandler(self.db, self.config_manager)
        self.sect_handler = SectHandler(self.db, self.config_manager)
        self.equipment_handler = EquipmentHandler(self.db, self.config_manager)
        self.gongfa_handler = GongfaHandler(self.db, self.config_manager)
        self.misc_handler = MiscHandler(self.db, self.config_manager)
        
        # 注册命令
        self._register_commands()
    
    async def on_enable(self):
        await self.db.init()
        
        # 启动后台管理服务器
        try:
            # 从配置文件获取管理密钥，如果没有则使用默认密钥
            admin_secret_key = self.config_manager.get_config("admin_secret_key", "default_admin_key_123456")
            
            # 准备服务实例
            services = {
                "database": self.db,
                "config_manager": self.config_manager
            }
            
            # 创建应用
            self.admin_app = create_app(admin_secret_key, services)
            
            # 启动服务器（在后台运行）
            import asyncio
            server_port = self.config_manager.get_config("admin_server_port", 8888)
            
            async def run_server():
                await self.admin_app.run_task(host="0.0.0.0", port=server_port)
            
            # 创建任务并运行
            asyncio.create_task(run_server())
            self.logger.info(f"修仙转后台管理服务器已启动，访问地址: http://localhost:{server_port}/")
        except Exception as e:
            self.logger.error(f"启动后台管理服务器失败: {e}")
            self.logger.error(traceback.format_exc())
        
        self.logger.info("修仙转插件已启用")
    
    async def on_disable(self):
        await self.db.close()
        self.logger.info("修仙转插件已禁用")
    
    def _register_commands(self):
        # 玩家相关命令
        self.register_command("我要修仙", self.handle_start_xiuxian)
        self.register_command("我的信息", self.handle_player_info)
        self.register_command("签到", self.handle_sign_in)
        self.register_command("闭关", self.handle_meditate)
        
        # 商店相关命令
        self.register_command("商店", self.handle_shop)
        self.register_command("我的背包", self.handle_backpack)
        self.register_command("购买", self.handle_buy)
        self.register_command("使用", self.handle_use_item)
        
        # 战斗相关命令
        self.register_command("挑战", self.handle_challenge)
        self.register_command("竞技场", self.handle_arena)
        
        # 境界相关命令
        self.register_command("突破", self.handle_breakthrough)
        
        # 宗门相关命令
        self.register_command("宗门", self.handle_sect)
        self.register_command("加入宗门", self.handle_join_sect)
        
        # 装备相关命令
        self.register_command("装备", self.handle_equipment)
        self.register_command("穿戴", self.handle_wear_equipment)
        
        # 功法相关命令
        self.register_command("功法", self.handle_gongfa)
        self.register_command("学习功法", self.handle_learn_gongfa)
        
        # 其他命令
        self.register_command("帮助", self.handle_help)
    
    # 玩家相关命令处理
    async def handle_start_xiuxian(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.player_handler.handle_start_xiuxian(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_player_info(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.player_handler.handle_player_info(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_sign_in(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.player_handler.handle_sign_in(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_meditate(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.player_handler.handle_meditate(event):
            result.append(msg)
        return "\n".join(result)
    
    # 商店相关命令处理
    async def handle_shop(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.shop_handler.handle_shop(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_backpack(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.shop_handler.handle_backpack(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_buy(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.shop_handler.handle_buy(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_use_item(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.shop_handler.handle_use_item(event):
            result.append(msg)
        return "\n".join(result)
    
    # 战斗相关命令处理
    async def handle_challenge(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.combat_handler.handle_challenge(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_arena(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.combat_handler.handle_arena(event):
            result.append(msg)
        return "\n".join(result)
    
    # 境界相关命令处理
    async def handle_breakthrough(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.realm_handler.handle_breakthrough(event):
            result.append(msg)
        return "\n".join(result)
    
    # 宗门相关命令处理
    async def handle_sect(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.sect_handler.handle_sect(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_join_sect(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.sect_handler.handle_join_sect(event):
            result.append(msg)
        return "\n".join(result)
    
    # 装备相关命令处理
    async def handle_equipment(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.equipment_handler.handle_equipment(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_wear_equipment(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.equipment_handler.handle_wear_equipment(event):
            result.append(msg)
        return "\n".join(result)
    
    # 功法相关命令处理
    async def handle_gongfa(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.gongfa_handler.handle_gongfa(event):
            result.append(msg)
        return "\n".join(result)
    
    async def handle_learn_gongfa(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.gongfa_handler.handle_learn_gongfa(event):
            result.append(msg)
        return "\n".join(result)
    
    # 其他命令处理
    async def handle_help(self, event: AstrMessageEvent) -> str:
        result = []
        async for msg in self.misc_handler.handle_help(event):
            result.append(msg)
        return "\n".join(result)