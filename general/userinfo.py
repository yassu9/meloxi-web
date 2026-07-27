import discord
from discord.ext import commands
from ui.embeds import create_embed
from config.emojis import section, arrow
from config.settings import COLOR_PRIMARY

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="userinfo", aliases=["ui", "whois"])
    async def user_info(self, ctx: commands.Context, user: discord.Member = None):
        """View information about a user."""
        target = user or ctx.author
        
        # Identity Logic (fetch_user for banner)
        try:
            full_user = await self.bot.fetch_user(target.id)
            banner_url = full_user.banner.url if full_user.banner else None
        except:
            banner_url = None
            
        created = int(target.created_at.timestamp())
        joined = int(target.joined_at.timestamp()) if hasattr(target, "joined_at") and target.joined_at else None
        
        # Permissions Logic
        perms_to_check = {
            "Administrator": "administrator",
            "Manage Server": "manage_guild",
            "Manage Roles": "manage_roles",
            "Manage Channels": "manage_channels",
            "Manage Messages": "manage_messages",
            "Manage Webhooks": "manage_webhooks",
            "Manage Nicknames": "manage_nicknames",
            "Manage Emojis": "manage_expressions",
            "Moderate Members": "moderate_members"
        }
        
        key_perms = []
        if hasattr(target, "guild_permissions"):
            for name, attr in perms_to_check.items():
                if getattr(target.guild_permissions, attr):
                    key_perms.append(name)
        
        # UI Assembly
        embed = create_embed(user=ctx.author, bot_user=self.bot.user, show_footer=True)
        embed.set_author(name="User Info", icon_url=self.bot.user.display_avatar.url)
        embed.set_thumbnail(url=target.display_avatar.url)
        if banner_url:
            embed.set_image(url=banner_url)
        
        if hasattr(target, "color"):
            embed.color = target.color if target.color.value != 0 else COLOR_PRIMARY

        # 1. Section: Information
        u_type = "Bot" if target.bot else "Human"
        embed.add_field(
            name=f"{section} Information",
            value=f"> {arrow} **Name**: {target.name}\n> {arrow} **ID**: `{target.id}`\n> {arrow} **Type**: {u_type}",
            inline=False
        )

        # 2. Section: Dates
        dates_val = f"> {arrow} **Created**: <t:{created}:f> (<t:{created}:R>)"
        if joined:
            dates_val += f"\n> {arrow} **Joined**: <t:{joined}:f> (<t:{joined}:R>)"
        embed.add_field(name=f"{section} Dates", value=dates_val, inline=False)

        # 3. Section: Member Status (If in server)
        if isinstance(target, discord.Member):
            roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
            boosting = f"<t:{int(target.premium_since.timestamp())}:R>" if target.premium_since else "No"
            
            embed.add_field(
                name=f"{section} Member Status",
                value=(
                    f"> {arrow} **Top Role**: {target.top_role.mention}\n"
                    f"> {arrow} **Boosting**: {boosting}\n"
                    f"> {arrow} **RolesCount**: `{len(roles)}`"
                ),
                inline=False
            )

        # 4. Section: Key Permissions
        if key_perms:
            embed.add_field(
                name=f"{section} Key Permissions",
                value=f"> {arrow} " + ", ".join(key_perms),
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserInfo(bot))

