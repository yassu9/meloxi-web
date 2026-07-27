import discord
from discord.ext import commands
from ui.embeds import create_embed
from config.emojis import section, arrow
from config.settings import COLOR_PRIMARY

class ServerInfoView(discord.ui.View):
    def __init__(self, bot, ctx, embed_base):
        super().__init__(timeout=60)
        self.bot = bot
        self.ctx = ctx
        self.embed_base = embed_base

    @discord.ui.button(label="Home", style=discord.ButtonStyle.gray)
    async def home(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.embed_base)

    @discord.ui.button(label="Icon", style=discord.ButtonStyle.gray)
    async def icon(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.ctx.guild.icon:
            return await interaction.response.send_message("This server has no icon.", ephemeral=True)
        embed = self.embed_base.copy()
        embed.set_image(url=self.ctx.guild.icon.url)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Banner", style=discord.ButtonStyle.gray)
    async def banner(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.ctx.guild.banner:
            return await interaction.response.send_message("This server has no banner.", ephemeral=True)
        embed = self.embed_base.copy()
        embed.set_image(url=self.ctx.guild.banner.url)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Features", style=discord.ButtonStyle.gray)
    async def features(self, interaction: discord.Interaction, button: discord.ui.Button):
        features = ", ".join([f.replace("_", " ").title() for f in self.ctx.guild.features]) or "None"
        embed = create_embed(user=self.ctx.author, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Server Features", icon_url=self.bot.user.display_avatar.url)
        embed.description = f"```\n{features}\n```"
        await interaction.response.edit_message(embed=embed)

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="serverinfo", aliases=["si"])
    async def server_info(self, ctx: commands.Context):
        """View detailed information about this server."""
        if not ctx.guild: return
        
        guild = ctx.guild
        created = int(guild.created_at.timestamp())
        
        # Member Stats Logic
        total = guild.member_count
        bots = sum(m.bot for m in guild.members)
        humans = total - bots
        
        # Channel Stats
        tc = len(guild.text_channels)
        vc = len(guild.voice_channels)
        roles = len(guild.roles)
        
        # UI Assembly
        embed = create_embed(user=ctx.author, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="Server Info", icon_url=self.bot.user.display_avatar.url)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # 1. Section: Server Information
        embed.add_field(
            name=f"{section} Server Information",
            value=(
                f"> {arrow} **Name**: {guild.name}\n"
                f"> {arrow} **ID**: `{guild.id}`\n"
                f"> {arrow} **Owner**: {guild.owner.mention}\n"
                f"> {arrow} **Created**: <t:{created}:D>"
            ),
            inline=False
        )

        # 2. Section: System Security
        embed.add_field(
            name=f"{section} System Security",
            value=(
                f"> {arrow} **Verify**: {str(guild.verification_level).title()}\n"
                f"> {arrow} **Filter**: {str(guild.explicit_content_filter).replace('_', ' ').title()}"
            ),
            inline=False
        )

        # 3. Section: Members (ANSI Block)
        ansi_members = (
            f"```ansi\n"
            f"\u001b[1;36mTotal  : \u001b[0m{total}\n"
            f"\u001b[1;32mHumans : \u001b[0m{humans}\n"
            f"\u001b[1;31mBots   : \u001b[0m{bots}\n"
            f"```"
        )
        embed.add_field(name=f"{section} Members", value=ansi_members, inline=False)

        # 4. Section: Counts
        embed.add_field(
            name=f"{section} Counts",
            value=(
                f"> {arrow} **Channels**: `{tc+vc}` (T: {tc} | V: {vc})\n"
                f"> {arrow} **Roles**: `{roles}`"
            ),
            inline=True
        )

        # 5. Section: Boosts
        embed.add_field(
            name=f"{section} Boosts",
            value=(
                f"> {arrow} **Level**: `{guild.premium_tier}`\n"
                f"> {arrow} **Total**: `{guild.premium_subscription_count}`"
            ),
            inline=True
        )

        view = ServerInfoView(self.bot, ctx, embed)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))

