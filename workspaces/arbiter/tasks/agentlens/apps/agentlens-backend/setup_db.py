from app.db.session import engine, Base
from app.models import models

def init_db():
    print("🚀 Initializing database and creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully.")

if __name__ == "__main__":
    init_db()
