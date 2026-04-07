import sys
sys.path.insert(0, '.')
from app import create_app
from src.extensions import db
from src.models.tenant import Tenant
from src.models.user import User
import bcrypt
import uuid

app = create_app()
with app.app_context():
    print("Fixing user passwords with bcrypt...")
    
    # Find or create tenant
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
        print(f"Created tenant: {tenant.name}")
    
    # Create/update admin user with bcrypt
    admin_email = 'admin@acme.com'
    admin_password = 'password123'
    admin_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    admin = User.query.filter_by(email=admin_email).first()
    if admin:
        admin.password_hash = admin_hash
        print(f"Updated {admin_email} password hash")
    else:
        admin = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=admin_email,
            password_hash=admin_hash,
            role='admin'
        )
        db.session.add(admin)
        print(f"Created {admin_email}")
    
    # Create/update zororo user with bcrypt
    zororo_email = 'admin@zororo.co.za'
    zororo_password = 'Admin1234!'
    zororo_hash = bcrypt.hashpw(zororo_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    zororo = User.query.filter_by(email=zororo_email).first()
    if zororo:
        zororo.password_hash = zororo_hash
        print(f"Updated {zororo_email} password hash")
    else:
        zororo = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=zororo_email,
            password_hash=zororo_hash,
            role='admin'
        )
        db.session.add(zororo)
        print(f"Created {zororo_email}")
    
    # Add a test user
    test_email = 'test@acme.com'
    test_password = 'test123'
    test_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    test_user = User.query.filter_by(email=test_email).first()
    if not test_user:
        test_user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=test_email,
            password_hash=test_hash,
            role='analyst'
        )
        db.session.add(test_user)
        print(f"Created {test_email}")
    
    db.session.commit()
    
    print("\n✅ Users in database:")
    for u in User.query.all():
        print(f"  {u.email} ({u.role})")
    
    print("\n🔑 Test credentials:")
    print(f"  admin@acme.com / password123")
    print(f"  admin@zororo.co.za / Admin1234!")
    print(f"  test@acme.com / test123")
