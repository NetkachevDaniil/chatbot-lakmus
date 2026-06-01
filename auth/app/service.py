from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg
from fastapi import HTTPException, status

from auth.db import record_to_dict
from auth.kafka import AuthEventProducer
from auth.schemas import LoginRequest, RegisterRequest
from auth.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, pool: asyncpg.Pool, producer: AuthEventProducer):
        self.pool = pool
        self.producer = producer

    async def register(self, payload: RegisterRequest) -> dict:
        async with self.pool.acquire() as connection:
            existing_user = await connection.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                payload.email.lower(),
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists",
                )

            user_id = uuid4()
            await connection.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name, role)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                payload.email.lower(),
                hash_password(payload.password),
                payload.full_name,
                payload.role,
            )

            user = await connection.fetchrow(
                """
                SELECT id, email, full_name, role, created_at
                FROM users
                WHERE id = $1
                """,
                user_id,
            )

            refresh_token_id = uuid4()
            tokens = self._build_token_pair(str(user_id), payload.role, refresh_token_id)
            refresh_payload = decode_token(tokens["refresh_token"])

            await connection.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, expires_at)
                VALUES ($1, $2, $3)
                """,
                refresh_token_id,
                user_id,
                datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
            )

        await self.producer.publish(
            "user_registered",
            {
                "user_id": str(user_id),
                "email": payload.email.lower(),
                "role": payload.role,
            },
        )
        return {"user": record_to_dict(user), "tokens": tokens}

    async def login(self, payload: LoginRequest) -> dict:
        async with self.pool.acquire() as connection:
            user = await connection.fetchrow(
                """
                SELECT id, email, password_hash, full_name, role, created_at
                FROM users
                WHERE email = $1
                """,
                payload.email.lower(),
            )
            if user is None or not verify_password(payload.password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                )

            refresh_token_id = uuid4()
            tokens = self._build_token_pair(str(user["id"]), user["role"], refresh_token_id)
            refresh_payload = decode_token(tokens["refresh_token"])

            await connection.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, expires_at)
                VALUES ($1, $2, $3)
                """,
                refresh_token_id,
                user["id"],
                datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
            )

        await self.producer.publish(
            "user_logged_in",
            {"user_id": str(user["id"]), "email": user["email"], "role": user["role"]},
        )

        user_data = record_to_dict(user)
        user_data.pop("password_hash", None)
        return {"user": user_data, "tokens": tokens}

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        token_id = UUID(payload["jti"])
        user_id = UUID(payload["sub"])

        async with self.pool.acquire() as connection:
            stored_token = await connection.fetchrow(
                """
                SELECT id, user_id, expires_at, revoked_at
                FROM refresh_tokens
                WHERE id = $1 AND user_id = $2
                """,
                token_id,
                user_id,
            )
            if stored_token is None or stored_token["revoked_at"] is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token is revoked or missing",
                )

            if stored_token["expires_at"] <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expired",
                )

            user = await connection.fetchrow(
                """
                SELECT id, email, full_name, role, created_at
                FROM users
                WHERE id = $1
                """,
                user_id,
            )
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            await connection.execute(
                "UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = $1",
                token_id,
            )

            new_refresh_token_id = uuid4()
            tokens = self._build_token_pair(str(user["id"]), user["role"], new_refresh_token_id)
            new_refresh_payload = decode_token(tokens["refresh_token"])

            await connection.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, expires_at)
                VALUES ($1, $2, $3)
                """,
                new_refresh_token_id,
                user["id"],
                datetime.fromtimestamp(new_refresh_payload["exp"], tz=timezone.utc),
            )

        await self.producer.publish(
            "token_refreshed",
            {"user_id": str(user["id"]), "refresh_token_id": str(new_refresh_token_id)},
        )

        return {"user": record_to_dict(user), "tokens": tokens}

    async def logout(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        token_id = UUID(payload["jti"])
        user_id = UUID(payload["sub"])

        async with self.pool.acquire() as connection:
            result = await connection.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW()
                WHERE id = $1 AND user_id = $2 AND revoked_at IS NULL
                """,
                token_id,
                user_id,
            )
            if result.endswith("0"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Refresh token not found",
                )

        await self.producer.publish(
            "user_logged_out",
            {"user_id": str(user_id), "refresh_token_id": str(token_id)},
        )

    async def get_current_user(self, access_token: str) -> dict:
        payload = decode_token(access_token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        async with self.pool.acquire() as connection:
            user = await connection.fetchrow(
                """
                SELECT id, email, full_name, role, created_at
                FROM users
                WHERE id = $1
                """,
                UUID(payload["sub"]),
            )
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            return record_to_dict(user)

    @staticmethod
    def _build_token_pair(user_id: str, role: str, refresh_token_id) -> dict[str, str]:
        return {
            "access_token": create_access_token(user_id=user_id, role=role),
            "refresh_token": create_refresh_token(
                user_id=user_id,
                role=role,
                refresh_token_id=str(refresh_token_id),
            ),
            "token_type": "bearer",
        }
