import discord
from discord.ext import commands
from discord.ui import View, Select
from ui.embeds import create_embed
import config.settings as settings
from utils.config_manager import ConfigManager
from utils.permissions import is_bot_owner
from config.emojis import section, arrow

class HelpDropdown(Select):
    def __init__(self, view: 'HelpView'):
        self.user_id = view.user_id
        
        # Categories mapped to simple labels
        opts = [
            ("Home", "🏠", "home"),
            ("Music Commands", "🎵", "music"),
            ("Identity & XP", "👤", "profile"),
            ("Management", "🛡️", "admin"),
            ("Utility & Stats", "📊", "info")
        ]
        
        options = [discord.SelectOption(label=l, emoji=e, value=v) for l, e, v in opts]
        super().__init__(placeholder="Choose a category...", options=options, custom_id="help_menu_select")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: 
            return await interaction.response.send_message("This menu is for the command user only.", ephemeral=True)
        
        view: HelpView = self.view
        val = self.values[0]
        
        if val == "home": await view.show_home(interaction)
        elif val == "music": await view.show_music(interaction)
        elif val == "profile": await view.show_profile(interaction)
        elif val == "admin": await view.show_admin(interaction)
        elif val == "info": await view.show_info(interaction)

class HelpView(View):
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.add_item(HelpDropdown(self))
        
        # Row 1: Home & All Commands
        from config.emojis import EMOJI_QUEUE, EMOJI_JOIN
        btn_home = discord.ui.Button(label="Home", style=discord.ButtonStyle.secondary, emoji=EMOJI_JOIN, row=1)
        btn_home.callback = self.home_callback
        self.add_item(btn_home)

        btn_all = discord.ui.Button(label="All Commands", style=discord.ButtonStyle.secondary, emoji=EMOJI_QUEUE, row=1)
        btn_all.callback = self.all_commands_callback
        self.add_item(btn_all)
        
        # Row 2: Invite & Support
        invite_link = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"
        self.add_item(discord.ui.Button(label="Invite Me", style=discord.ButtonStyle.link, url=invite_link, row=2))
        self.add_item(discord.ui.Button(label="Support", style=discord.ButtonStyle.link, url=settings.SUPPORT_SERVER, row=2))

    async def home_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: 
            return await interaction.response.send_message("This menu is for the command user only.", ephemeral=True)
        await self.show_home(interaction)

    async def all_commands_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: 
            return await interaction.response.send_message("This menu is for the command user only.", ephemeral=True)
        await self.show_all_commands(interaction)

    async def _get_embed_basics(self, interaction):
        prefix = "r!"
        if interaction.guild:
             try:
                 config = ConfigManager.get_server_config(str(interaction.guild.id))
                 if config.prefix: prefix = config.prefix
             except: pass
        return prefix

    async def show_home(self, interaction):
        prefix = await self._get_embed_basics(interaction)
        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        total_servers = len(self.bot.guilds)
        latency = round(self.bot.latency * 1000)
        
        # Simplified V5+ Home Page
        embed = create_embed(user=interaction.user, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name=f"{self.bot.user.name} | Help Center", icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        embed.description = (
            f"**Premium music for your community.**\n"
            f"Simple and powerful tools for your server."
        )
        
        embed.add_field(
            name=f"{section} **Performance**",
            value=f"```yaml\nServers: {total_servers}\nUsers: {total_members}\nPing: {latency}ms\n```",
            inline=True
        )
        
        embed.add_field(
            name=f"{section} **System Hub**",
            value=(
                f"> {arrow} **Owner**: `Yashuuuu`\n"
                # f"> {arrow} **Status**: `Verified Stable`"
            ),
            inline=True
        )
        
        embed.add_field(
            name=f"{section} **Quick Guide**",
            value=(
                f"> {arrow} Select a category below to see commands.\n"
                f"> {arrow} Click **All Commands** for the full list."
            ),
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_all_commands(self, interaction):
        embed = create_embed(user=interaction.user, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="All Command List", icon_url=self.bot.user.display_avatar.url)
        
        embed.add_field(
            name=f"{section} **Music & Playback**",
            value=f"> `/play`, `/pause`, `/resume`, `/stop`, `/skip`\n> `/seek`, `/loop`, `/shuffle`, `/volume`, `/queue`\n> `/nowplaying`, `/clear`, `/remove`, `/move`\n> `/join`, `/leave`, `/sad`, `/romantic`, `/suggest`",
            inline=False
        )
        embed.add_field(
            name=f"{section} **Administration**",
            value=f"> `/setup`, `/settings`, `/prefix`\n> `/setchannel`, `/setvoice`, `/refreshch`\n> `/247`, `/features list`, `/features toggle`, `/nuke`, `/purge`",
            inline=False
        )
        embed.add_field(
            name=f"{section} **Identity & Social**",
            value=f"> `/profile`, `/bio set`, `/bio clear`\n> `/level`, `/leaderboard`",
            inline=False
        )
        embed.add_field(
            name=f"{section} **System & Utils**",
            value=f">  `/ping`, `/botinfo`, `/serverinfo`\n> `/userinfo`, `/invited`, `/uptime`",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_music(self, interaction):
        embed = create_embed(user=interaction.user, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Music Player Controls", icon_url=self.bot.user.display_avatar.url)
        
        details = (
            f"{section} **Player Controls**\n"
            f"> `/play`, `/pause`, `/resume`, `/stop`\n"
            f"> `/skip`, `/seek`, `/loop`, `/shuffle`, `/volume`\n\n"
            f"{section} **Queue Tools**\n"
            f"> `/queue`, `/nowplaying`, `/clear`\n"
            f"> `/remove`, `/move`, `/join`, `/leave`\n\n"
            f"{section} **Moods**\n"
            f"> `/sad`, `/romantic`, `/suggest`"
        )
        embed.description = details
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_profile(self, interaction):
        embed = create_embed(user=interaction.user, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Identity & Ranking", icon_url=self.bot.user.display_avatar.url)
        
        details = (
            f"{section} **Profile Info**\n"
            f"> `/profile`, `/bio set`, `/bio clear`\n\n"
            f"{section} **XP & Ranking**\n"
            f"> `/level`, `/leaderboard`"
        )
        embed.description = details
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_admin(self, interaction):
        embed = create_embed(user=interaction.user, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Server Management", icon_url=self.bot.user.display_avatar.url)
        
        details = (
            f"{section} **Setup Tools**\n"
            f"> `/setup`, `/settings`, `/prefix`\n"
            f"> `/setchannel`, `/setvoice`, `/refreshch`\n\n"
            f"{section} **Feature Toggles**\n"
            f"> `/247`, `/features list`, `/features toggle`\n\n"
            f"{section} **Maintenance**\n"
            f"> `/nuke`, `/purge`"
        )
        embed.description = details
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_info(self, interaction):
        embed = create_embed(user=interaction.user, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Reporting & Stats", icon_url=self.bot.user.display_avatar.url)
        
        details = (
            f"{section} **Bot/User Info**\n"
            f"> `/botinfo`, `/serverinfo`, `/userinfo`\n\n"
            f"{section} **Stats**\n"
            f"> `/ping`, `/uptime`, `/invited`"
        )
        embed.description = details
        await interaction.response.edit_message(embed=embed, view=self)

class HelpMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="help", aliases=["h"])
    async def help(self, ctx: commands.Context):
        """Open the flagship-tier help center."""
        prefix = "r!"
        if ctx.guild:
             try:
                 config = ConfigManager.get_server_config(str(ctx.guild.id))
                 if config.prefix: prefix = config.prefix
             except: pass

        view = HelpView(self.bot, ctx.author.id)
        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        total_servers = len(self.bot.guilds)
        latency = round(self.bot.latency * 1000)
        
        # Simplified V5+ Home Page
        embed = create_embed(user=ctx.author, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name=f"{self.bot.user.name} | Help Center", icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        embed.description = (
            f"**Premium music for your community.**\n"
            f"Simple and powerful tools for your server."
        )
        
        embed.add_field(
            name=f"{section} **Performance**",
            value=f"```yaml\nServers: {total_servers}\nUsers: {total_members}\nPing: {latency}ms\n```",
            inline=True
        )
        
        embed.add_field(
            name=f"{section} **System Hub**",
            value=(
                f"> {arrow} **Owner**: `Yashuuuu`\n"
                # f"> {arrow} **Status**: `Verified Stable`"
            ),
            inline=True
        )
        
        embed.add_field(
            name=f"{section} **Quick Guide**",
            value=(
                f"> {arrow} Select a category below to see commands.\n"
                f"> {arrow} Click **All Commands** for the full list."
            ),
            inline=False
        )
        
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpMenu(bot))
