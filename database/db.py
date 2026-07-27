"""
Database Connection Manager.
"""

# ==============================================================================
# 🔌 DATABASE SETUP
# ==============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import StaticPool
from config.settings import DATABASE_URL

Base = declarative_base()

# Configure Engine (SQLite vs Postgres support)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # SQLAlchemy requires 'postgresql://', but some hosts (like Railway/Heroku) provide 'postgres://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Optimize for production PostgreSQL
    engine = create_engine(
        DATABASE_URL, 
        echo=False,
        pool_size=10,            # 10 active connections
        max_overflow=20,         # Allow up to 20 extra connections during burst
        pool_timeout=30,         # Wait 30s before giving up
        pool_recycle=1800,      # Recycle connections after 30 mins
        pool_pre_ping=True      # Check connection validity before using
    )

# Session Factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    """Dependency for DB session."""
    db = SessionLocal()
    try: yield db
    finally: db.close()

def patch_database():
    """Ensures missing columns are added to existing tables."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    
    # 1. user_profiles -> np_expires_at
    try:
        columns = [c['name'] for c in inspector.get_columns('user_profiles')]
        if 'np_expires_at' not in columns:
            with engine.begin() as conn:
                # Add np_expires_at (SQLite vs Postgres)
                if DATABASE_URL.startswith("sqlite"):
                    conn.execute(text("ALTER TABLE user_profiles ADD COLUMN np_expires_at DATETIME"))
                else:
                    conn.execute(text("ALTER TABLE user_profiles ADD COLUMN np_expires_at TIMESTAMP"))
                print("✅ Patched database: Added np_expires_at to user_profiles")
    except Exception as e:
        print(f"⚠️ Error during database patch: {e}")

def init_db():
    """Initialize Tables."""
    import database.models
    Base.metadata.create_all(bind=engine)
    patch_database()
