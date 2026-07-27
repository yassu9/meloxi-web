"""
Premium Cog for Meloxi.
Handles premium status checking and benefits display.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

from datetime import datetime, timezone
import discord
import asyncio
from discord.ext import commands, tasks

from config.emojis import arrow
from ui.embeds import create_success_embed, create_embed, create_error_embed, create_info_embed
from utils.permissions import is_premium
from database.db import SessionLocal
from database.models import UserProfile
from premium.subscriptions import SubscriptionManager
from utils.time import ist_now
from utils.logger import logger

# ==============================================================================
# 💎 PREMIUM COG
# ==============================================================================

class Premium(commands.Cog):
    """Commands related to Premium features."""
    
    def __init__(self, bot):
        self.bot = bot
        self.sub_manager = SubscriptionManager()
        self.check_premium_expiration.start()
        
    def cog_unload(self):
        self.check_premium_expiration.cancel()
    
    # ==========================================================================
    # 🌟 COMMANDS
    # ==========================================================================

    @commands.hybrid_command(name="premium", aliases=["prem"])
    async def premium(self, ctx: commands.Context):
        """Check premium status & perks."""
        user_id = ctx.author.id
        has_premium = is_premium(user_id)

        # 1. Non-Premium State
        if not has_premium:
            embed = create_embed("Premium Status", None, user=ctx.author, bot_user=self.bot.user, show_footer=True)
            desc = []
            desc.append(f"**__PREMIUM PERKS__**")
            desc.append(f"> {arrow} **Benefit**: `Unlock the bot's full power`")
            desc.append(f"> {arrow} **Advantage**: `No-Prefix Mode`")
            desc.append("")
            desc.append(f"**__WHAT YOU GET__**")
            desc.append(f"> {arrow} **No-Prefix**: Use commands without prefix.\n> {arrow} **Support**: Direct help from developers.\n> {arrow} **Elite**: Profile status & badges.\n> {arrow} **Fast XP**: 2x level progress.")
            desc.append("")
            desc.append(f"**__HOW TO GET IT__**")
            desc.append(f"```yaml\nCommand:  /buy | /subscribe\nPayment:  Razorpay Secure\nStatus:   Ready\n```")
            embed.description = "\n".join(desc)
            await ctx.send(embed=embed)
            return

        # 2. Premium State (Fetch Details)
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
            expires_at = profile.premium_expires_at if profile else None
        finally: db.close()

        # Calculate Expiry
        # ist_now is naive UTC
        now = ist_now()
        
        if expires_at:
            remaining = max((expires_at - now).days, 0)
            expiry_str = expires_at.strftime("%d %b %Y")
            rem_str = f"{remaining} days"
        else:
            expiry_str = "Lifetime"
            rem_str = "∞"

        # Show Status
        embed = create_success_embed(
            "Premium Active",
            f"> {arrow} **Status:** Active\n"
            f"> {arrow} **Expires:** `{expiry_str}`\n"
            f"> {arrow} **Remaining:** `{rem_str}`\n\n"
            f"**__UNLOCKED FEATURES__**\n"
            f"> {arrow} No-Prefix Mode\n"
            f"> {arrow} Premium Badge\n"
            f"> {arrow} Direct Support",
            user=ctx.author,
            bot_user=self.bot.user,
            show_footer=True
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="buy", aliases=["subscribe"])
    async def buy(self, ctx: commands.Context):
        """Get Premium Subscription Link."""
        if is_premium(ctx.author.id):
             await ctx.send(embed=create_info_embed("All Set", "You already have Meloxi Premium!", user=ctx.author, bot_user=self.bot.user))
             return

        if not self.sub_manager.is_enabled():
            await ctx.send(embed=create_error_embed("Wait", "The payment system is currently offline.", user=ctx.author, bot_user=self.bot.user))
            return
            
        msg = await ctx.send(embed=create_embed("Generating Link", "Please wait while we connect to Razorpay...", user=ctx.author))
        
        link = await self.sub_manager.create_subscription(ctx.author.id)
        
        if link:
            from config.emojis import EMOJI_PREMIUM
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Pay Now", emoji=EMOJI_PREMIUM, url=link))
            
            embed = create_success_embed(
                "Buy Premium",
                f"Use the button below to get Premium.\n\n> {arrow} It will activate automatically after payment.",
                user=ctx.author
            )
            await msg.edit(embed=embed, view=view)
        else:
             await msg.edit(embed=create_error_embed("Error", "Failed to generate link. Try again later.", user=ctx.author))


    # ==========================================================================
    # 🕒 BACKGROUND TASKS
    # ==========================================================================

    @tasks.loop(minutes=1)
    async def check_premium_expiration(self):
        """Centralized expiration check for Premium and No-Prefix."""
        now = ist_now()
        
        def fetch_expired():
            db = SessionLocal()
            try:
                # 1. Check Premium & Linked NP
                expired_pm = db.query(UserProfile).filter(
                    UserProfile.premium == True,
                    UserProfile.premium_expires_at != None,
                    UserProfile.premium_expires_at <= now
                ).all()

                # 2. Check Independent NP
                expired_np = db.query(UserProfile).filter(
                    UserProfile.no_prefix == True,
                    UserProfile.np_expires_at != None,
                    UserProfile.np_expires_at <= now
                ).all()

                pm_ids = []
                np_ids = []

                for p in expired_pm:
                    pm_ids.append(p.user_id)
                    p.premium = False
                    p.premium_expires_at = None
                    p.no_prefix = False # Force clear NP
                    p.np_expires_at = None
                    
                for p in expired_np:
                    np_ids.append(p.user_id)
                    p.no_prefix = False
                    p.np_expires_at = None

                db.commit()
                return pm_ids, np_ids
            except Exception as e:
                db.rollback()
                logger.error(f"Error in premium check loop DB: {e}")
                return [], []
            finally:
                db.close()

        pm_ids, np_ids = await asyncio.to_thread(fetch_expired)

        for p_id in pm_ids:
            logger.info(f"Premium Expired for {p_id}")
            
            # Audit Log
            await self.bot.log_bot_event("premium_expire", f"Premium expired for {p_id}")

            try:
                user = self.bot.get_user(int(p_id)) or await self.bot.fetch_user(int(p_id))
                if user:
                    embed = create_info_embed(
                         "Premium Ended", 
                         f"Hi {user.name}, your premium time has ended.\nYour perks are now turned off, but you can always renew using `/buy`.\n\nThanks for being with us! 🎵",
                         bot_user=self.bot.user
                    )
                    await user.send(embed=embed)
            except: pass

        for p_id in np_ids:
            logger.info(f"No-Prefix Expired for {p_id}")
            
            # Audit Log
            await self.bot.log_bot_event("np_expire", f"No-Prefix expired for {p_id}")

            try:
                user = self.bot.get_user(int(p_id)) or await self.bot.fetch_user(int(p_id))
                if user:
                    embed = create_info_embed(
                         "Access Ended", 
                         f"Hi {user.name}, your independent 'No-Prefix' access has ended.\nYou can still use the bot with its regular prefix. Have a great day! 🎵",
                         bot_user=self.bot.user
                    )
                    await user.send(embed=embed)
            except: pass

    @check_premium_expiration.before_loop
    async def before_check_premium_expiration(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Premium(bot))