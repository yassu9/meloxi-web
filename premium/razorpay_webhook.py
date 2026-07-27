"""
Razorpay Webhook Handler.
Async endpoint for payment events using aiohttp.
"""

import hmac, hashlib, json
from aiohttp import web
from config.settings import RAZORPAY_WEBHOOK_SECRET
from premium.subscriptions import SubscriptionManager
import logging

logger = logging.getLogger("meloxi.webhook")

class WebhookServer:
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_post('/razorpay/webhook', self.handle_webhook)
        self.app.router.add_post('/vote-webhook', self.handle_vote_webhook)
        self.runner = None
        self.site = None

    async def verify_signature(self, body: bytes, signature: str) -> bool:
        """Validate webhook source."""
        if not RAZORPAY_WEBHOOK_SECRET: return True # Dev mode
        gen = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(gen, signature)

    async def handle_webhook(self, request):
        """Endpoint."""
        try:
            body = await request.read()
            sig = request.headers.get("X-Razorpay-Signature")

            if not await self.verify_signature(body, sig):
                logger.warning("Invalid Webhook Signature")
                return web.json_response({"error": "Invalid signature"}, status=400)

            payload = json.loads(body.decode())
            event = payload.get("event")
            
            # Use Manager
            manager = SubscriptionManager()
            # Inject Bot for Role updates if needed
            manager.bot = self.bot 
            
            if await manager.handle_webhook(event, payload):
                logger.info(f"Processed Event: {event}")
                return web.json_response({"status": "ok"})
            else:
                return web.json_response({"status": "ignored"})
                
        except Exception as e:
            logger.error(f"Webhook Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_vote_webhook(self, request):
        """Vote Reward Endpoint."""
        try:
            # Top.gg sends 'user' (ID), 'isPremium' (Optional), etc.
            # Generic lists might send 'user_id'
            body = await request.json()
            user_id = body.get("user") or body.get("user_id")
            
            if not user_id:
                return web.json_response({"error": "Missing user_id"}, status=400)

            # 1. Grant 12 Hours Premium/No-Prefix
            from datetime import timedelta
            from utils.time import ist_now
            from database.db import SessionLocal
            from database.models import UserProfile
            from ui.embeds import create_embed, create_info_embed, arrow

            expires_at = ist_now() + timedelta(hours=12)
            
            db = SessionLocal()
            try:
                p = db.query(UserProfile).filter_by(user_id=str(user_id)).first()
                if not p:
                    p = UserProfile(user_id=str(user_id), premium=True, no_prefix=True, premium_expires_at=expires_at, np_expires_at=expires_at)
                    db.add(p)
                else:
                    p.premium = True
                    p.no_prefix = True
                    p.premium_expires_at = expires_at
                    p.np_expires_at = expires_at
                db.commit()
                logger.info(f"Vote Reward: Granted 12h to {user_id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Vote DB Error: {e}")
                return web.json_response({"error": "Database error"}, status=500)
            finally:
                db.close()

            # 2. Notify User via DM
            try:
                user = await self.bot.fetch_user(int(user_id))
                if user:
                    dm_embed = create_embed(
                        title="Vote Reward",
                        description=(
                            f"**Thank you for voting!**\n"
                            f"You have been granted **12 hours** of No-Prefix access.\n\n"
                            f"> {arrow} **Expires**: <t:{int(expires_at.timestamp())}:R>"
                        ),
                        color=0x00FF9C, # Green
                        bot_user=self.bot.user
                    )
                    dm_embed.set_author(name="Vote Reward", icon_url=self.bot.user.display_avatar.url)
                    dm_embed.set_footer(text="💡 Tip: try /variables")
                    await user.send(embed=dm_embed)
            except Exception as e:
                logger.warning(f"Failed to send vote DM to {user_id}: {e}")

            return web.json_response({"status": "ok", "message": "Reward granted"})

        except Exception as e:
            logger.error(f"Vote Webhook Error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def start(self):
        """Start the web server."""
        import os
        port = int(os.environ.get("PORT", 6000))
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '0.0.0.0', port)
        await self.site.start()
        logger.info(f"Webhook Server running on port {port}")
    
    async def stop(self):
        """Stop server."""
        if self.runner: await self.runner.cleanup()