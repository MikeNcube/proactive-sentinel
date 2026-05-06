#!/usr/bin/env python
"""
Cross-platform setup script for Proactive Sentinel
Runs database migrations and seeds data
"""

import subprocess
import sys
import time
import os


def run_command(cmd, check=True, capture=False):
    """Run a shell command and print output"""
    print(f">>> {' '.join(cmd)}")
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(result.stderr, file=sys.stderr)
        if check and result.returncode != 0:
            sys.exit(result.returncode)
        return result
    else:
        return subprocess.run(cmd, check=check)


def main():
    print("=" * 50)
    print("Proactive Sentinel - Database Setup")
    print("=" * 50)

    # Check Docker
    print("\n1. Checking Docker...")
    result = run_command(["docker", "info"], check=False, capture=True)
    if result.returncode != 0:
        print("ERROR: Docker is not running. Please start Docker Desktop first.")
        sys.exit(1)
    print("Docker is running")

    # Start services
    print("\n2. Starting services...")
    run_command(["docker-compose", "up", "-d"])
    time.sleep(10)

    # Run migrations
    print("\n3. Running database migrations...")
    run_command(["docker-compose", "exec", "-T", "app", "python", "-m", "flask", "db", "upgrade"])

    # Setup test database
    print("\n4. Setting up test database...")
    run_command(
        [
            "docker-compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "sentinel",
            "-c",
            "DROP DATABASE IF EXISTS sentinel_test;",
        ],
        check=False,
    )
    run_command(
        [
            "docker-compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "sentinel",
            "-c",
            "CREATE DATABASE sentinel_test;",
        ]
    )
    run_command(
        [
            "docker-compose",
            "exec",
            "-T",
            "app",
            "bash",
            "-c",
            "export DATABASE_URL=postgresql://sentinel:dev_password@postgres:5432/sentinel_test && python -m flask db upgrade",
        ]
    )

    # Seed database
    print("\n5. Seeding database...")
    run_command(["docker-compose", "exec", "-T", "app", "python", "scripts/seed_data.py"])

    print("\n" + "=" * 50)
    print("Setup complete")
    print("=" * 50)
    print("\nNext steps:")
    print("  1. Run tests: docker-compose exec app pytest tests/ -v")
    print("  2. Test API: curl.exe http://localhost:5000/health")
    print("  3. View logs: docker-compose logs -f")


if __name__ == "__main__":
    main()
