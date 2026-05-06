import sys
sys.path.insert(0, '/app')
from app import create_app
from src.extensions import db
from src.models.tenant import Tenant
from src.models.user import User
import uuid

app = create_app()
with app.app_context():
    print('Setting up database with Werkzeug password hashing...')
    
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
    else:
        print(f'Tenant exists: {tenant.name}')
    
    # Create admin user using set_password method
    admin = User.query.filter_by(email='admin@acme.com').first()
    if admin:
        admin.set_password('password123')
        print(f'Updated password for {admin.email}')
    else:
        admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email='admin@acme.com',
            role='admin'
        )
        admin.set_password('password123')
        db.session.add(admin)
        print(f'Created {admin.email}')
    
    # Create zororo user using set_password method
    zororo = User.query.filter_by(email='admin@zororo.co.za').first()
    if zororo:
        zororo.set_password('Admin1234!')
        print(f'Updated password for {zororo.email}')
    else:
        zororo = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email='admin@zororo.co.za',
            role='admin'
        )
        zororo.set_password('Admin1234!')
        db.session.add(zororo)
        print(f'Created {zororo.email}')
    
    db.session.commit()
    
    print('\nUsers in database:')
    for u in User.query.all():
        print(f'  {u.email} (hash starts with: {u.password_hash[:20]}...)')
    
    print('\nLogin credentials:')
    print('  admin@acme.com / password123')
    print('  admin@zororo.co.za / Admin1234!')
    print('\nPasswords hashed with Werkzeug format (pbkdf2:sha256)')
