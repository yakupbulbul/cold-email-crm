import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models import Base, Domain, Mailbox

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if domain exists
        existing_domain = db.query(Domain).filter_by(name="example.com").first()
        if not existing_domain:
            print("Seeding testing domain example.com...")
            domain = Domain(name="example.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            print("Seeding test mailbox dev@example.com...")
            mailbox = Mailbox(
                domain_id=domain.id,
                email="dev@example.com",
                display_name="Dev Example",
                smtp_host="mail.example.com",
                smtp_port=587,
                smtp_username="dev@example.com",
                smtp_password_encrypted="super-secret-placeholder",
                imap_host="mail.example.com",
                imap_port=993,
                imap_username="dev@example.com",
                imap_password_encrypted="super-secret-placeholder",
                warmup_enabled=True,
                status="active"
            )
            db.add(mailbox)
            db.commit()
            
            print("Seed completed successfully.")
        else:
            print("Database already seeded.")
            
    except Exception as e:
        db.rollback()
        print(f"Failed to seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
