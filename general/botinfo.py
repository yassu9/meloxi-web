import discord
from discord.ext import commands
import time
import platform
import psutil
import os
from ui.embeds import create_embed
from config.emojis import section, arrow
from config.settings import COLOR_PRIMARY, BOT_TAGLINE, CREATOR_CREDIT, SUPPORT_SERVER

class BotInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @commands.hybrid_command(name="ping", aliases=["latency"])
    async def ping(self, ctx: commands.Context):
        """Check bot latency."""
        start = time.perf_counter()
        from ui.embeds import create_info_embed
        msg = await ctx.send(embed=create_info_embed(None, "Pinging...", bot_user=self.bot.user))
        end = time.perf_counter()
        
        ws_latency = round(self.bot.latency * 1000)
        api_latency = round((end - start) * 1000)
        
        embed = create_embed(user=ctx.author, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Latency Check", icon_url=self.bot.user.display_avatar.url)
        embed.description = f"> {arrow} **System**: `{ws_latency}ms`\n> {arrow} **Speed**: `{api_latency}ms`"
        
        if ws_latency > 200: embed.color = 0xFFD166
        elif ws_latency > 500: embed.color = 0xFF3B3B
        else: embed.color = 0x00FF9C
        
        await msg.edit(embed=embed)

    @commands.hybrid_command(name="botinfo", aliases=["about", "bi", "stats", "system", "st"])
    async def info_command(self, ctx: commands.Context):
        """View premium bot statistics and system health."""
        # 📊 Stats Calculations
        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        total_servers = len(self.bot.guilds)
        total_cmds = len(list(self.bot.walk_commands()))
        shards = self.bot.shard_count or 1
        
        # 🕒 Uptime Formatting
        uptime_raw = time.time() - self.start_time
        m, s = divmod(int(uptime_raw), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        uptime_str = f"{d}d {h}h {m}m"
        
        # 💻 Resource Usage
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info().rss / 1024 / 1024 # MB
        cpu = psutil.cpu_percent()
        
        # 🎨 UI Assembly
        invite_url = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"
        
        embed = create_embed(user=ctx.author, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name=f"{self.bot.user.name}", icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.description = f"***{BOT_TAGLINE}***\n\u200b"
        
        # 1. Section: Identity
        created_at = int(self.bot.user.created_at.timestamp())
        embed.add_field(
            name=f"{section} Identity",
            value=(
                f"> {arrow} **Name**: `{self.bot.user.name}`\n"
                f"> {arrow} **ID**: `{self.bot.user.id}`\n"
                f"> {arrow} **Birth**: <t:{created_at}:D> (<t:{created_at}:R>)"
            ),
            inline=False
        )

        # 2. Section: Network Statistics (ANSI)
        ansi_stats = (
            f"```ansi\n"
            f"\u001b[1;36mServers : \u001b[0m{total_servers}\n"
            f"\u001b[1;32mUsers   : \u001b[0m{total_members}\n"
            f"\u001b[1;35mShards  : \u001b[0m{shards}\n"
            f"\u001b[1;33mCmds    : \u001b[0m{total_cmds}\n"
            f"```"
        )
        embed.add_field(name=f"{section} Network Statistics", value=ansi_stats, inline=False)

        # 3. Section: System Health (YAML)
        health_yaml = (
            f"```yaml\n"
            f"Latency: {round(self.bot.latency * 1000)}ms\n"
            f"CPU:     {cpu}%\n"
            f"RAM:     {mem:.1f} MB\n"
            f"Uptime:  {uptime_str}\n"
            f"```"
        )
        embed.add_field(name=f"{section} System Health", value=health_yaml, inline=False)

        # 4. Section: Resource Hub
        embed.add_field(
            name=f"{section} **Resource Hub**",
            value=(
                f"> {arrow} **Developer**: `Yashuuu`\n"
                # f"> {arrow} **Engine**: `V2-Core (Stable)`\n"
                f"> {arrow} **Source**: [Invite]({invite_url}) • [Support]({SUPPORT_SERVER})"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"{CREATOR_CREDIT} | {uptime_str} uptime", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else self.bot.user.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="uptime", aliases=["up"])
    async def uptime(self, ctx: commands.Context):
        """Check how long the bot has been online."""
        uptime_raw = time.time() - self.start_time
        m, s = divmod(int(uptime_raw), 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        uptime_str = f"{d}d {h}h {m}m {s}s"
        
        embed = create_embed(user=ctx.author, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Uptime Status", icon_url=self.bot.user.display_avatar.url)
        embed.description = (
            f"> {arrow} **{self.bot.user.name} Online**: `{uptime_str}`\n"
            f"> {arrow} **Session Start**: <t:{int(self.start_time)}:F>"
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotInfo(bot))
