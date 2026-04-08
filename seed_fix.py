import sys
sys.path.insert(0, '/app')
from app import create_app
from src.extensions import db
from src.models.tenant import Tenant
from src.models.user import User
import bcrypt
import uuid

app = create_app()
with app.app_context():
    print('Setting up database...')
    
    # Create tenant
    tenant = Tenant.query.filter_by(subdomain='acme').first()
    if not tenant:
        tenant = Tenant(
            id=uuid.uuid4(),
            name='Acme Insurance',
            subdomain='acme',
            status='active'
        )
        db.session.add(tenant)
        db.session.commit()
        print(f'Created tenant: {tenant.name}')
    
    # Create admin user
    admin = User.query.filter_by(email='admin@acme.com').first()
    if not admin:
        admin_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode()
        admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email='admin@acme.com',
            password_hash=admin_hash,
            role='admin'
        )
        db.session.add(admin)
        print('Created admin@acme.com')
    
    # Create zororo user
    zororo = User.query.filter_by(email='admin@zororo.co.za').first()
    if not zororo:
        zororo_hash = bcrypt.hashpw(b'Admin1234!', bcrypt.gensalt()).decode()
        zororo = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email='admin@zororo.co.za',
            password_hash=zororo_hash,
            role='admin'
        )
        db.session.add(zororo)
        print('Created admin@zororo.co.za')
    
    db.session.commit()
    print('\nUsers in database:')
    for u in User.query.all():
        print(f'  {u.email}')
    
    print('\nLogin credentials:')
    print('  admin@acme.com / password123')
    print('  admin@zororo.co.za / Admin1234!')
