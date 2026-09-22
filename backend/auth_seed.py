from app.db.session import SessionLocal
from app.models import User
from app.api.routes import _hash_password
from sqlalchemy import select

with SessionLocal() as db:
    email='demo@aimpf.local'
    if not db.scalar(select(User).where(User.email==email)):
        db.add(User(email=email,password_hash=_hash_password('aimpf-demo-password')))
        db.commit()
        print('Created demo user: demo@aimpf.local / aimpf-demo-password')
    else:
        print('Demo user already exists')
