"""
One-time local setup script — creates the initial admin user with a
system-generated temporary password.

There's deliberately no HTTP "create user" endpoint (see auth_service.py's
create_user docstring for why) — this is a single-owner local tool, so
this script is how the very first user gets created.

Run once, from the project root, inside the venv:
    python -m backend.seed_admin

The temporary password is printed ONCE to the console and never stored in
plaintext anywhere. Log in with it via POST /auth/login, then you'll be
required to set a real password via POST /auth/reset-password
(must_reset_password starts True).
"""

import secrets

from backend.services.auth_service import create_user, USERS_PATH


def main():

    username = input("Admin username [admin]: ").strip() or "admin"

    temp_password = secrets.token_urlsafe(12)

    try:
        create_user(username, temp_password)

    except ValueError as e:
        print(f"Could not create user: {e}")
        print(f"If you meant to reset it, delete that entry from {USERS_PATH} first.")
        return

    print("\nAdmin user created.")
    print(f"  Username: {username}")
    print(f"  Temporary password: {temp_password}")
    print("\nThis password is shown ONLY here — it is not stored in plaintext")
    print("anywhere, only its PBKDF2 hash. Log in with POST /auth/login, then")
    print("you'll be required to set a real password via POST /auth/reset-password.\n")


if __name__ == "__main__":
    main()