#!/usr/bin/env python3
"""One-time script to exchange AmoCRM authorization code for tokens.

Usage:
    1. Create an external integration in AmoCRM settings
    2. Copy client_id, client_secret, redirect_uri to .env
    3. Click "Authorize" in AmoCRM integration settings to get the auth code
    4. Run: python -m scripts.setup_amocrm <AUTH_CODE>

The script will:
    - Exchange the code for access_token + refresh_token
    - Save both to the amo_tokens table in the database
    - The bot will then auto-refresh tokens on each restart
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import aiohttp

# Ensure project root is in path
sys.path.insert(0, ".")

from src.config import settings
from src.db.engine import async_session, engine
from src.db.models import AmoToken


async def exchange_code(auth_code: str) -> dict:
    """Exchange authorization code for tokens via AmoCRM OAuth."""
    base_url = f"https://{settings.AMOCRM_SUBDOMAIN}.amocrm.ru"
    payload = {
        "client_id": settings.AMOCRM_CLIENT_ID,
        "client_secret": settings.AMOCRM_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": settings.AMOCRM_REDIRECT_URI,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/oauth2/access_token",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"ERROR: AmoCRM returned status {resp.status}")
                print(f"Response: {body}")
                sys.exit(1)

            return await resp.json()


async def save_tokens(data: dict) -> None:
    """Save tokens to the database."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])

    async with async_session() as session:
        token = AmoToken(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=expires_at,
        )
        session.add(token)
        await session.commit()

    await engine.dispose()


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.setup_amocrm <AUTH_CODE>")
        print()
        print("Get the auth code from AmoCRM:")
        print("  Settings -> Integrations -> Your integration -> Authorize")
        sys.exit(1)

    auth_code = sys.argv[1]

    # Validate settings
    if not settings.AMOCRM_SUBDOMAIN:
        print("ERROR: AMOCRM_SUBDOMAIN not set in .env")
        sys.exit(1)
    if not settings.AMOCRM_CLIENT_ID:
        print("ERROR: AMOCRM_CLIENT_ID not set in .env")
        sys.exit(1)
    if not settings.AMOCRM_CLIENT_SECRET:
        print("ERROR: AMOCRM_CLIENT_SECRET not set in .env")
        sys.exit(1)

    print(f"Exchanging auth code for tokens...")
    print(f"  Subdomain: {settings.AMOCRM_SUBDOMAIN}")
    print(f"  Client ID: {settings.AMOCRM_CLIENT_ID[:8]}...")
    print(f"  Redirect URI: {settings.AMOCRM_REDIRECT_URI}")
    print()

    data = await exchange_code(auth_code)

    print(f"Tokens received:")
    print(f"  Access token: {data['access_token'][:20]}...")
    print(f"  Refresh token: {data['refresh_token'][:20]}...")
    print(f"  Expires in: {data['expires_in']} seconds")
    print()

    print("Saving to database...")
    await save_tokens(data)

    print("Done! Tokens saved to amo_tokens table.")
    print("The bot will auto-refresh tokens from now on.")


if __name__ == "__main__":
    asyncio.run(main())
