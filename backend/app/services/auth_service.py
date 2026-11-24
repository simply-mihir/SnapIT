"""
Account logic: register, password login, Google login.
"""
import re
from typing import Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthError, UserExistsError
from app.core.security import hash_password, verify_password
from app.models.user import User

_GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"
_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ----- Password accounts -----

    async def register(self, username: str, password: str) -> User:
        existing = await self.db.execute(
            select(User).where(func.lower(User.username) == username)
        )
        if existing.scalar_one_or_none() is not None:
            raise UserExistsError("That username is already taken.")
        user = User(
            username=username,
            display_name=username,
            password_hash=hash_password(password),
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise UserExistsError("That username is already taken.")
        await self.db.refresh(user)
        return user

    async def login(self, identifier: str, password: str) -> User:
        """`identifier` is a username or an email (for accounts with both)."""
        ident = identifier.strip().lower()
        result = await self.db.execute(
            select(User).where(
                (func.lower(User.username) == ident) | (func.lower(User.email) == ident)
            )
        )
        user = result.scalar_one_or_none()
        # Same error + same work for unknown user and wrong password, so the
        # response doesn't reveal which usernames exist.
        stored = user.password_hash if user else None
        if not verify_password(password, stored) or user is None:
            raise AuthError("Invalid username or password.")
        return user

    # ----- Google -----

    async def login_with_google(self, credential: str) -> User:
        if not settings.GOOGLE_CLIENT_ID:
            raise AuthError("Google sign-in is not configured.")
        info = await self._verify_google_token(credential)
        sub, email = info["sub"], info.get("email")

        user = (
            await self.db.execute(select(User).where(User.google_sub == sub))
        ).scalar_one_or_none()
        if user is not None:
            return user

        # Link to an existing account with the same (Google-verified) email.
        if email:
            user = (
                await self.db.execute(
                    select(User).where(func.lower(User.email) == email.lower())
                )
            ).scalar_one_or_none()
            if user is not None:
                user.google_sub = sub
                await self.db.commit()
                return user

        user = User(
            email=email.lower() if email else None,
            google_sub=sub,
            display_name=info.get("name") or (email.split("@")[0] if email else "User"),
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    @staticmethod
    async def _verify_google_token(credential: str) -> dict:
        """Verify a Google ID token via Google's tokeninfo endpoint."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(_GOOGLE_TOKENINFO, params={"id_token": credential})
        except httpx.HTTPError:
            raise AuthError("Could not reach Google to verify sign-in.")
        if resp.status_code != 200:
            raise AuthError("Invalid Google credential.")
        info = resp.json()
        if info.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise AuthError("Google credential was issued for a different app.")
        if info.get("iss") not in _GOOGLE_ISSUERS:
            raise AuthError("Invalid Google credential issuer.")
        if str(info.get("email_verified")).lower() != "true":
            raise AuthError("Google email is not verified.")
        if not info.get("sub"):
            raise AuthError("Invalid Google credential.")
        return info
