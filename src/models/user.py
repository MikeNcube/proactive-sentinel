"""
User model with encrypted PII fields
"""

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, DateTime, Boolean, Enum
from src.extensions import db
from src.utils.encryption import field_encryption
import bcrypt
import uuid
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.id'), nullable=False)
    
    email = db.Column(String(255), nullable=False, unique=True)
    role = db.Column(Enum('admin', 'analyst', 'viewer', name='user_roles'), default='analyst')
    mfa_enabled = db.Column(Boolean, default=False)
    
    phone_encrypted = db.Column(String(500))
    full_name_encrypted = db.Column(String(500))
    mfa_secret_encrypted = db.Column(String(500))
    address_encrypted = db.Column(db.Text)
    
    password_hash = db.Column(String(255), nullable=False)
    
    created_at = db.Column(DateTime, default=datetime.utcnow)
    last_login = db.Column(DateTime)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def phone(self):
        return field_encryption.decrypt(self.phone_encrypted) if self.phone_encrypted else None
    
    @phone.setter
    def phone(self, value):
        self.phone_encrypted = field_encryption.encrypt(value) if value else None
    
    @property
    def full_name(self):
        return field_encryption.decrypt(self.full_name_encrypted) if self.full_name_encrypted else None
    
    @full_name.setter
    def full_name(self, value):
        self.full_name_encrypted = field_encryption.encrypt(value) if value else None
    
    @property
    def address(self):
        return field_encryption.decrypt(self.address_encrypted) if self.address_encrypted else None
    
    @address.setter
    def address(self, value):
        self.address_encrypted = field_encryption.encrypt(value) if value else None
    
    def set_mfa_secret(self, secret):
        self.mfa_secret_encrypted = field_encryption.encrypt(secret) if secret else None
    
    def get_mfa_secret(self):
        return field_encryption.decrypt(self.mfa_secret_encrypted) if self.mfa_secret_encrypted else None
    
    def set_password(self, password):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self, include_sensitive=False):
        data = {
            'id': str(self.id),
            'email': self.email,
            'role': self.role,
            'mfa_enabled': self.mfa_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
        if include_sensitive:
            data['full_name'] = self.full_name
            data['phone'] = self.phone
            data['address'] = self.address
        return data
    
    def __repr__(self):
        return f'<User {self.email}>'
