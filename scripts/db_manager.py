#!/usr/bin/env python3
"""
Interactive Database Manager for LabOS
Simple tool to view and manage users without SQL commands
"""

import sys
import os
from pathlib import Path
import asyncio
from datetime import datetime

# Add parent directory to path (stella-be root)
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
# Load .env from stella-be root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
from app.models import User, UserStatus

# Database connections - read from environment variables
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

if not DB_USER or not DB_PASSWORD:
    print("\n❌ Error: Database credentials not configured!")
    print("Please set DB_USER and DB_PASSWORD in stella-be/.env file")
    print("\nAdd these lines to .env:")
    print("  DB_USER=your_db_user")
    print("  DB_PASSWORD=your_db_password")
    sys.exit(1)

DB_NAME_DEV = os.getenv('DEV_DB_NAME', 'stella_chat_dev')
DB_NAME_PROD = os.getenv('DB_NAME', 'stella_chat')

DEV_DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@localhost:5432/{DB_NAME_DEV}"
PROD_DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@localhost:5433/{DB_NAME_PROD}"


class DatabaseManager:
    def __init__(self, db_url: str, db_name: str):
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.db_name = db_name
    
    async def get_session(self):
        async with self.async_session() as session:
            yield session
    
    async def list_users(self, status_filter: str = None, limit: int = 20):
        """List users with optional status filter"""
        async with self.async_session() as session:
            query = select(User)
            
            if status_filter:
                try:
                    status_enum = UserStatus(status_filter)
                    query = query.where(User.status == status_enum)
                except ValueError:
                    print(f"❌ Invalid status: {status_filter}")
                    return []
            
            query = query.order_by(User.created_at.desc()).limit(limit)
            result = await session.execute(query)
            users = result.scalars().all()
            return users
    
    async def get_user_by_email(self, email: str):
        """Get user by email"""
        async with self.async_session() as session:
            query = select(User).where(User.email == email)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def get_user_stats(self):
        """Get user statistics"""
        async with self.async_session() as session:
            # Total users
            total = await session.execute(select(func.count(User.id)))
            total_count = total.scalar()
            
            # Count by status
            stats = {}
            for status in UserStatus:
                count_query = select(func.count(User.id)).where(User.status == status)
                result = await session.execute(count_query)
                stats[status.value] = result.scalar()
            
            return {
                'total': total_count,
                'by_status': stats
            }
    
    async def approve_user(self, email: str, admin_id: str = "manual"):
        """Approve a user by email"""
        async with self.async_session() as session:
            query = select(User).where(User.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "User not found"
            
            if user.status == UserStatus.APPROVED:
                return False, "User already approved"
            
            user.status = UserStatus.APPROVED
            user.approved_at = datetime.utcnow()
            user.approved_by = admin_id
            
            await session.commit()
            return True, f"User {email} approved"
    
    async def set_admin(self, email: str, is_admin: bool = True):
        """Set or unset admin status for a user"""
        async with self.async_session() as session:
            query = select(User).where(User.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "User not found"
            
            user.is_admin = is_admin
            await session.commit()
            
            action = "granted" if is_admin else "revoked"
            return True, f"Admin privileges {action} for {email}"
    
    async def delete_user(self, email: str):
        """Delete a user by email (use with caution!)"""
        async with self.async_session() as session:
            query = select(User).where(User.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "User not found"
            
            await session.delete(user)
            await session.commit()
            return True, f"User {email} deleted"


def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_user_table(users):
    """Pretty print users in a table format"""
    if not users:
        print("\n  No users found.")
        return
    
    print(f"\n  {'Email':<35} {'Status':<12} {'Admin':<7} {'Created':<12}")
    print("  " + "-"*68)
    
    for user in users:
        email = user.email[:33] + ".." if len(user.email) > 35 else user.email
        status = user.status.value
        is_admin = "✓" if user.is_admin else ""
        created = user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
        
        print(f"  {email:<35} {status:<12} {is_admin:<7} {created:<12}")


def print_user_detail(user):
    """Print detailed user information"""
    if not user:
        print("\n  User not found.")
        return
    
    print(f"\n  Email:           {user.email}")
    full_name = user.name or f"{user.first_name or ''} {user.last_name or ''}".strip() or 'N/A'
    print(f"  Name:            {full_name}")
    print(f"  Status:          {user.status.value}")
    print(f"  Is Admin:        {'Yes' if user.is_admin else 'No'}")
    print(f"  Job Title:       {user.job_title or 'N/A'}")
    print(f"  Organization:    {user.organization or 'N/A'}")
    print(f"  Country:         {user.country or 'N/A'}")
    print(f"  Experience:      {user.experience_level or 'N/A'}")
    print(f"  Use Case:        {user.use_case or 'N/A'}")
    print(f"  Created:         {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}")
    print(f"  Last Login:      {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}")
    print(f"  Approved At:     {user.approved_at.strftime('%Y-%m-%d %H:%M:%S') if user.approved_at else 'N/A'}")
    print(f"  Approved By:     {user.approved_by or 'N/A'}")


async def view_and_manage_user(db_manager: DatabaseManager, users):
    """View user details and perform actions"""
    if not users:
        print("\n  No users to select.")
        return
    
    print("\n  Select a user:")
    for idx, user in enumerate(users, 1):
        admin = "👑" if user.is_admin else "  "
        print(f"  {idx:2}. {admin} {user.email}")
    print("   0. Back")
    
    choice = input("\n  Enter number: ").strip()
    
    if choice == '0':
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(users):
            user = users[idx]
            
            while True:
                print_header(f"User Details: {user.email}")
                print_user_detail(user)
                
                print("\n  Actions:")
                print("    1. Approve this user")
                print("    2. Grant admin privileges")
                print("    3. Revoke admin privileges")
                print("    4. Delete this user (⚠️  dangerous)")
                print("    0. Back")
                
                action = input("\n  Choose action (0-4): ").strip()
                
                if action == '0':
                    break
                elif action == '1':
                    success, msg = await db_manager.approve_user(user.email)
                    print(f"\n  {'✅' if success else '❌'} {msg}")
                    if success:
                        # Refresh user data
                        user = await db_manager.get_user_by_email(user.email)
                    input("\n  Press Enter to continue...")
                elif action == '2':
                    success, msg = await db_manager.set_admin(user.email, True)
                    print(f"\n  {'✅' if success else '❌'} {msg}")
                    if success:
                        user = await db_manager.get_user_by_email(user.email)
                    input("\n  Press Enter to continue...")
                elif action == '3':
                    success, msg = await db_manager.set_admin(user.email, False)
                    print(f"\n  {'✅' if success else '❌'} {msg}")
                    if success:
                        user = await db_manager.get_user_by_email(user.email)
                    input("\n  Press Enter to continue...")
                elif action == '4':
                    confirm = input(f"\n  ⚠️  DELETE {user.email}? Type 'DELETE' to confirm: ").strip()
                    if confirm == 'DELETE':
                        success, msg = await db_manager.delete_user(user.email)
                        print(f"\n  {'✅' if success else '❌'} {msg}")
                        input("\n  Press Enter to continue...")
                        if success:
                            break
                    else:
                        print("\n  ⏭️  Cancelled")
                        input("\n  Press Enter to continue...")
        else:
            print("\n  ❌ Invalid selection")
    except ValueError:
        print("\n  ❌ Invalid input")


async def interactive_menu(db_manager: DatabaseManager):
    """Interactive menu for database operations"""
    
    while True:
        print_header(f"LabOS Database Manager - {db_manager.db_name}")
        
        print("\n  📊 View & Manage:")
        print("    1. Browse all users (with actions)")
        print("    2. Browse waitlist users (with actions)")
        print("    3. Browse approved users (with actions)")
        print("    4. Browse admin users (with actions)")
        
        print("\n  📈 Statistics:")
        print("    5. View user statistics")
        
        print("\n  🔍 Search:")
        print("    6. Search and manage user by email")
        
        print("\n  🔄 Other:")
        print("    0. Exit")
        
        choice = input("\n  Enter your choice (0-6): ").strip()
        
        try:
            if choice == '0':
                print("\n  👋 Goodbye!")
                break
            
            elif choice == '1':
                print_header("All Users (Latest 20)")
                users = await db_manager.list_users(limit=20)
                print_user_table(users)
                await view_and_manage_user(db_manager, users)
            
            elif choice == '2':
                print_header("Waitlist Users")
                users = await db_manager.list_users(status_filter='waitlist', limit=50)
                print_user_table(users)
                await view_and_manage_user(db_manager, users)
            
            elif choice == '3':
                print_header("Approved Users")
                users = await db_manager.list_users(status_filter='approved', limit=50)
                print_user_table(users)
                await view_and_manage_user(db_manager, users)
            
            elif choice == '4':
                print_header("Admin Users")
                users = await db_manager.list_users(limit=100)
                admins = [u for u in users if u.is_admin]
                print_user_table(admins)
                await view_and_manage_user(db_manager, admins)
            
            elif choice == '5':
                print_header("User Statistics")
                stats = await db_manager.get_user_stats()
                print(f"\n  Total Users:      {stats['total']}")
                print(f"  Waitlist:         {stats['by_status'].get('waitlist', 0)}")
                print(f"  Approved:         {stats['by_status'].get('approved', 0)}")
                print(f"  Rejected:         {stats['by_status'].get('rejected', 0)}")
                print(f"  Suspended:        {stats['by_status'].get('suspended', 0)}")
                input("\n  Press Enter to continue...")
            
            elif choice == '6':
                email = input("\n  Enter email address: ").strip()
                user = await db_manager.get_user_by_email(email)
                if user:
                    await view_and_manage_user(db_manager, [user])
                else:
                    print("\n  ❌ User not found")
                    input("\n  Press Enter to continue...")
            
            else:
                print("\n  ❌ Invalid choice. Please try again.")
                input("\n  Press Enter to continue...")
        
        except Exception as e:
            print(f"\n  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            input("\n  Press Enter to continue...")


async def main():
    print("\n" + "="*70)
    print("  🗄️  LabOS Database Manager")
    print("="*70)
    print("\n  Select database:")
    print("    1. Development (localhost:5432)")
    print("    2. Production (localhost:5433)")
    print("    0. Exit")
    
    choice = input("\n  Enter your choice (0-2): ").strip()
    
    if choice == '0':
        print("\n  👋 Goodbye!")
        return
    elif choice == '1':
        db_manager = DatabaseManager(DEV_DB_URL, "Development")
    elif choice == '2':
        db_manager = DatabaseManager(PROD_DB_URL, "Production")
    else:
        print("\n  ❌ Invalid choice")
        return
    
    try:
        await interactive_menu(db_manager)
    except KeyboardInterrupt:
        print("\n\n  👋 Interrupted by user")
    finally:
        await db_manager.engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

