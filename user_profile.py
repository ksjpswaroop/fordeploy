#!/usr/bin/env python3
"""
user_profile.py
Manage per-user preferences:
- Blacklisted companies
- Blacklisted skills
(No resume handling here)
"""

import json
import os

USERS_FILE = "users.json"


def create_user_profile(user_id, name, blacklist_companies=None, blacklist_skills=None):
    """Create or update a user profile and save into users.json"""
    if blacklist_companies is None:
        blacklist_companies = []
    if blacklist_skills is None:
        blacklist_skills = []

    new_profile = {
        "user_id": user_id,
        "name": name,
        "blacklist_companies": blacklist_companies,
        "blacklist_skills": blacklist_skills,
    }

    users = []
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                users = []

    # Replace existing or add new
    for i, u in enumerate(users):
        if u["user_id"] == user_id:
            users[i] = new_profile
            break
    else:
        users.append(new_profile)

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

    print(f"✅ User profile saved for {user_id}")


def load_user_profile(user_id):
    """Load a user profile from users.json"""
    if not os.path.exists(USERS_FILE):
        raise FileNotFoundError("users.json not found. Please create a profile first.")

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

    for u in users:
        if u["user_id"] == user_id:
            return u

    raise ValueError(f"User {user_id} not found.")


if __name__ == "__main__":
    # Instead of requiring CLI args, just create a default sample profile
    create_user_profile(
        user_id="skanda",
        name="Skanda Chittuluru",
        blacklist_companies=["Google", "Microsoft", "Amazon", "Accenture", "The Hershey Company", "Tiger Analytics"],
        blacklist_skills=["php", "cold calling", "cobol", "telemarketing"]
    )
