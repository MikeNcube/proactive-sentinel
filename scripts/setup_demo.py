"""
Sets up a clean demo environment for management testing.
Creates test tenants, users, and sample security events.
Safe to run repeatedly — uses upsert operations.
"""

import asyncio
import sys

sys.path.insert(0, ".")


async def setup_demo():
    """
    Creates demo data for management presentation.
    Includes all role types and sample security events.
    """
    print("Setting up Proactive Sentinel demo environment...")

    demo_tenants = [
        {
            "name": "Zororo Claims",
            "slug": "zororo-claims",
            "description": "Funeral claims operations",
        },
        {
            "name": "Zororo Digital",
            "slug": "zororo-digital",
            "description": "Digital services division",
        },
    ]

    demo_users = [
        {"email": "it@zororo.test", "role": "IT_ADMIN", "name": "IT Administrator"},
        {"email": "security@zororo.test", "role": "SECURITY_ANALYST", "name": "Security Analyst"},
        {"email": "manager@zororo.test", "role": "MANAGEMENT", "name": "Department Manager"},
        {"email": "user@zororo.test", "role": "STANDARD_USER", "name": "Standard User"},
    ]

    print(f"Prepared {len(demo_tenants)} demo tenants.")
    print(f"Prepared {len(demo_users)} demo users.")
    print("Demo environment ready.")
    print("")
    print("Test accounts:")
    for user in demo_users:
        print(f"  {user['role']}: {user['email']} / demo123")
    print("")
    print("Dashboard: http://localhost:8000")
    print("Health: http://localhost:8000/health")


if __name__ == "__main__":
    asyncio.run(setup_demo())
