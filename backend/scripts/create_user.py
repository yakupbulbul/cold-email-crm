import os
import sys
import argparse

# Add the backend app to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_user(email: str, password: str, is_admin: bool = False):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists.")
            return
        
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_admin=is_admin,
            is_active=True,
            full_name="Bootstrap Admin" if is_admin else "Regular User"
        )
        db.add(user)
        db.commit()
        print(f"User {email} created successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new user")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="User password")
    parser.add_argument("--admin", action="store_true", help="Create as admin")
    
    args = parser.parse_args()
    create_user(args.email, args.password, args.admin)
