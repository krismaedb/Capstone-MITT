#!/usr/bin/env python3
"""
HealthClinic User Creator
Creates staff users with standard password: g3company!@#

Usage:
  python3 create_user.py                    # Create default users
  python3 create_user.py --list             # List all users
  python3 create_user.py --reset-passwords  # Reset all passwords to g3company!@#
"""

import sys
import os

# Add parent directory to path so we can import app
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app import create_app, db
from app.models import User

DEFAULT_PASSWORD = 'g3company!@#'

def create_user(username, email, full_name, role, phone=None):
    """Create a new user with default password"""
    app = create_app()
    
    with app.app_context():
        # Check if user exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"⚠️  User '{username}' already exists! Skipping...")
            return False
        
        # Create new user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            phone=phone,
            is_active=True
        )
        user.set_password(DEFAULT_PASSWORD)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ Created: {username:20} | {role:10} | {full_name}")
        return True

def list_users():
    """List all existing users"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        print("\n" + "="*80)
        print("CURRENT USERS IN DATABASE")
        print("="*80)
        print(f"{'Username':<20} {'Role':<12} {'Full Name':<30} {'Status'}")
        print("-"*80)
        for user in users:
            status = "Active" if user.is_active else "Inactive"
            print(f"{user.username:<20} {user.role:<12} {user.full_name:<30} {status}")
        print("-"*80)
        print(f"Total Users: {len(users)}\n")

def reset_all_passwords():
    """Reset all user passwords to default"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        print("\n🔑 Resetting all passwords to: g3company!@#\n")
        for user in users:
            user.set_password(DEFAULT_PASSWORD)
            print(f"✅ Reset password for: {user.username}")
        
        db.session.commit()
        print(f"\n✅ All {len(users)} user passwords have been reset!\n")

def main():
    """Main function"""
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            list_users()
            return
        elif sys.argv[1] == '--reset-passwords':
            reset_all_passwords()
            return
        elif sys.argv[1] == '--help':
            print(__doc__)
            return
    
    print("\n" + "="*80)
    print("HEALTHCLINIC USER CREATOR")
    print("="*80)
    print(f"Default Password: {DEFAULT_PASSWORD}\n")
    
    # Define default users to create
    default_users = [
        {
            'username': 'admin',
            'email': 'admin@healthclinic.local',
            'full_name': 'System Administrator',
            'role': 'admin',
            'phone': '204-555-0100'
        },
        {
            'username': 'nurse.maria',
            'email': 'maria@healthclinic.local',
            'full_name': 'Maria Gonzales',
            'role': 'nurse',
            'phone': '204-555-0103'
        },
        {
            'username': 'admin.billing',
            'email': 'billing@healthclinic.local',
            'full_name': 'Billing Administrator',
            'role': 'admin',
            'phone': '204-555-0104'
        },
        {
            'username': 'nurse.emily',
            'email': 'emily@healthclinic.local',
            'full_name': 'Emily Rodriguez',
            'role': 'nurse',
            'phone': '204-555-0106'
        }
    ]
    
    # Create all default users
    created = 0
    skipped = 0
    
    for user_data in default_users:
        if create_user(**user_data):
            created += 1
        else:
            skipped += 1
    
    print("\n" + "-"*80)
    print(f"✅ Created: {created} new users")
    print(f"⚠️  Skipped: {skipped} existing users")
    print("-"*80 + "\n")
    
    # Show all users
    list_users()

if __name__ == '__main__':
    main()
