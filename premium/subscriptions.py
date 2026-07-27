"""
Subscription Manager.
Handles Razorpay integration.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

try:
    import razorpay
except ImportError:
    razorpay = None
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
from database.db import SessionLocal
from database.models import Subscription, UserProfile
from config.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_PLAN_ID

# ==============================================================================
# 💎 SUBSCRIPTION MANAGER
# ==============================================================================

class SubscriptionManager:
    """Razorpay Subscription Logic."""
    
    def __init__(self):
        self.client = None
        if razorpay and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
            try:
                self.client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
            except: pass
    
    def is_enabled(self) -> bool:
        return self.client is not None and RAZORPAY_PLAN_ID is not None
    
    async def create_subscription(self, user_id: str) -> Optional[str]:
        """Generate subscription link."""
        if not self.is_enabled(): return None
        try:
            # Create Subscription (10 years monthly)
            resp = self.client.subscription.create({
                'plan_id': RAZORPAY_PLAN_ID,
                'total_count': 120, 
                'quantity': 1,
                'customer_notify': 1,
                'notes': {'user_id': str(user_id)}
            })
            return resp.get('short_url')
        except Exception as e:
            print(f"Sub Error: {e}")
            return None
    
    async def handle_webhook(self, event: str, payload: Dict) -> bool:
        """Process Webhook."""
        if not self.client: return False
        
        db = SessionLocal()
        try:
            if event == 'subscription.activated':
                await self._activate(db, payload)
            elif event == 'subscription.charged':
                await self._renew(db, payload)
            elif event == 'subscription.cancelled':
                await self._cancel(db, payload)
            elif event == 'subscription.expired':
                await self._expire(db, payload)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Webhook Error: {e}")
            return False
        finally: db.close()
    
    # ==========================================================================
    # 🔄 INTERNAL HANDLERS
    # ==========================================================================

    async def _activate(self, db, payload):
        """Handle activation."""
        data = payload.get('payload', {}).get('subscription', {})
        uid = data.get('notes', {}).get('user_id')
        if not uid: return
        
        # Check duplicate
        sid = data.get('id')
        exists = db.query(Subscription).filter_by(razorpay_subscription_id=sid).first()
        if exists: return

        sub = Subscription(
            user_id=uid,
            subscription_id=sid,
            plan_id=data.get('plan_id'),
            status='active',
            started_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            razorpay_subscription_id=sid
        )
        db.add(sub)
        
        # Grant Premium
        p = db.query(UserProfile).filter_by(user_id=uid).first()
        if not p:
            p = UserProfile(user_id=uid, premium=True, no_prefix=True, premium_expires_at=sub.expires_at)
            db.add(p)
        else:
            p.premium = True; p.no_prefix = True; p.premium_expires_at = sub.expires_at
    
    async def _renew(self, db, payload):
        """Handle renewal."""
        data = payload.get('payload', {}).get('subscription', {})
        sub = db.query(Subscription).filter_by(razorpay_subscription_id=data.get('id')).first()
        if sub:
            sub.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            sub.status = 'active'
            
            p = db.query(UserProfile).filter_by(user_id=sub.user_id).first()
            if p: p.premium = True; p.premium_expires_at = sub.expires_at
    
    async def _cancel(self, db, payload):
        """Handle cancellation."""
        data = payload.get('payload', {}).get('subscription', {})
        sub = db.query(Subscription).filter_by(razorpay_subscription_id=data.get('id')).first()
        if sub: sub.status = 'cancelled'
        
        # Optionally revoke premium immediately or wait for expiry? 
        # User requested: "PM REMOVE SUBSCRIPTION ON -> PM ON, SUBSCRIPTION KHTAM -> PM REMOVE"
        # Usually subscription cancelled means no *future* charging, but current period is valid.
        # However, for simplicity and safety, we mark as cancelled. logic in permissions handles expiry.
    
    async def _expire(self, db, payload):
        """Handle expiration."""
        data = payload.get('payload', {}).get('subscription', {})
        sub = db.query(Subscription).filter_by(razorpay_subscription_id=data.get('id')).first()
        if sub:
            sub.status = 'expired'
            p = db.query(UserProfile).filter_by(user_id=sub.user_id).first()
            if p: p.premium = False; p.no_prefix = False

    async def sync_all_subscriptions(self) -> int:
        """Fetch all active subscriptions from Razorpay and sync DB."""
        if not self.is_enabled(): return 0
        
        count = 0
        try:
            # 1. Fetch Active
            limit = 100
            resp = self.client.subscription.all({'status': 'active', 'count': limit})
            items = resp.get('items', [])
            print(f"DEBUG: Razorpay returned {len(items)} active subscriptions.")
            
            db = SessionLocal()
            try:
                for item in items:
                    sid = item.get('id')
                    notes = item.get('notes', {})
                    uid = notes.get('user_id')
                    
                    print(f"DEBUG: Processing {sid} | Status: {item.get('status')} | UserID: {uid}")
                    
                    if not uid or not sid:
                        print("DEBUG: Skipping - Missing UserID or SID.")
                        continue
                    
                    # Upsert Subscription
                    sub = db.query(Subscription).filter_by(razorpay_subscription_id=sid).first()
                    end_at = item.get('charge_at') or item.get('end_at')
                    expires = datetime.fromtimestamp(end_at, timezone.utc) if end_at else datetime.now(timezone.utc) + timedelta(days=30)
                    
                    if not sub:
                        sub = Subscription(
                            user_id=uid, subscription_id=sid, plan_id=item.get('plan_id'),
                            status='active', started_at=datetime.now(timezone.utc),
                            expires_at=expires, razorpay_subscription_id=sid
                        )
                        db.add(sub)
                    else:
                        sub.status = 'active'
                        sub.expires_at = expires
                    
                    # Update Profile
                    p = db.query(UserProfile).filter_by(user_id=uid).first()
                    if not p:
                        p = UserProfile(user_id=uid, premium=True, no_prefix=True, premium_expires_at=expires)
                        db.add(p)
                    else:
                        p.premium = True
                        p.no_prefix = True
                        p.premium_expires_at = expires
                    
                    count += 1
                
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Db Sync Error: {e}")
            finally: db.close()
            
        except Exception as e:
            print(f"Sync API Error: {e}")
        
        return count
