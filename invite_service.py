"""Azure-backed invite codes and signed access sessions."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache

from azure.core import MatchConditions
from azure.core.exceptions import HttpResponseError, ResourceModifiedError, ResourceNotFoundError
from azure.data.tables import TableClient
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


COOKIE_NAME = "career_ai_access"
SESSION_MAX_AGE = 7 * 24 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_FAILED_ATTEMPTS = 5


class InviteConfigurationError(RuntimeError):
    """Invite authentication has not been configured correctly."""


class InviteUnavailableError(RuntimeError):
    """The Azure invite store could not be reached."""


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise InviteConfigurationError(f"Invite access is not configured: {name} is missing.")
    return value


@lru_cache(maxsize=1)
def invite_table() -> TableClient:
    return TableClient.from_connection_string(
        _required_setting("INVITE_STORAGE_CONNECTION_STRING"),
        table_name=os.getenv("INVITE_TABLE_NAME", "CareerInvites").strip()
        or "CareerInvites",
    )


@lru_cache(maxsize=1)
def session_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        _required_setting("INVITE_SESSION_SECRET"), salt="career-ai-access-v1"
    )


def normalize_code(code: str) -> str:
    return "".join(str(code or "").strip().upper().split())


def code_hash(code: str) -> str:
    return hashlib.sha256(normalize_code(code).encode("utf-8")).hexdigest()


def _is_expired(value: object) -> bool:
    if not value:
        return False
    try:
        expires = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires <= datetime.now(timezone.utc)
    except ValueError:
        return True


def _invite_is_active(entity: dict) -> bool:
    return bool(entity.get("Enabled", False)) and not _is_expired(
        entity.get("ExpiresAt")
    )


def redeem_invite(code: str) -> str | None:
    """Atomically consume one use of a valid invite and return its row key."""
    row_key = code_hash(code)
    if len(normalize_code(code)) < 12:
        return None
    table = invite_table()
    for _attempt in range(3):
        try:
            entity = table.get_entity("invite", row_key)
        except ResourceNotFoundError:
            return None
        except HttpResponseError as exc:
            raise InviteUnavailableError("Invite verification is temporarily unavailable.") from exc
        uses = int(entity.get("Uses", 0))
        if not _invite_is_active(entity) or uses >= int(entity.get("MaxUses", 1)):
            return None
        entity["Uses"] = uses + 1
        entity["LastUsedAt"] = datetime.now(timezone.utc).isoformat()
        try:
            table.update_entity(
                entity,
                mode="merge",
                etag=entity.metadata["etag"],
                match_condition=MatchConditions.IfNotModified,
            )
            return row_key
        except ResourceModifiedError:
            continue
        except HttpResponseError as exc:
            raise InviteUnavailableError("Invite verification is temporarily unavailable.") from exc
    return None


def issue_session(invite_row_key: str) -> str:
    return session_serializer().dumps(
        {"invite": invite_row_key, "session": uuid.uuid4().hex}
    )


def validate_session(token: str) -> bool:
    if not token:
        return False
    try:
        payload = session_serializer().loads(token, max_age=SESSION_MAX_AGE)
        row_key = str(payload.get("invite", ""))
        if len(row_key) != 64:
            return False
        entity = invite_table().get_entity("invite", row_key)
        return _invite_is_active(entity)
    except (BadSignature, SignatureExpired, ResourceNotFoundError):
        return False
    except HttpResponseError as exc:
        raise InviteUnavailableError("Access verification is temporarily unavailable.") from exc


def csrf_token() -> str:
    return session_serializer().dumps({"purpose": "invite-login", "nonce": uuid.uuid4().hex})


def validate_csrf(token: str) -> bool:
    try:
        payload = session_serializer().loads(token, max_age=60 * 60)
        return hmac.compare_digest(str(payload.get("purpose", "")), "invite-login")
    except (BadSignature, SignatureExpired):
        return False


def _client_key(client_ip: str) -> str:
    secret = _required_setting("INVITE_SESSION_SECRET").encode("utf-8")
    return hmac.new(secret, client_ip.encode("utf-8"), hashlib.sha256).hexdigest()


def login_is_rate_limited(client_ip: str) -> bool:
    try:
        entity = invite_table().get_entity("ratelimit", _client_key(client_ip))
    except ResourceNotFoundError:
        return False
    except HttpResponseError as exc:
        raise InviteUnavailableError("Invite verification is temporarily unavailable.") from exc
    if int(time.time()) - int(entity.get("WindowStarted", 0)) >= LOGIN_WINDOW_SECONDS:
        return False
    return int(entity.get("Failures", 0)) >= MAX_FAILED_ATTEMPTS


def record_failed_login(client_ip: str) -> None:
    table = invite_table()
    row_key = _client_key(client_ip)
    now = int(time.time())
    for _attempt in range(3):
        try:
            entity = table.get_entity("ratelimit", row_key)
            if now - int(entity.get("WindowStarted", 0)) >= LOGIN_WINDOW_SECONDS:
                entity["WindowStarted"], entity["Failures"] = now, 1
            else:
                entity["Failures"] = int(entity.get("Failures", 0)) + 1
            table.update_entity(
                entity,
                mode="merge",
                etag=entity.metadata["etag"],
                match_condition=MatchConditions.IfNotModified,
            )
            return
        except ResourceNotFoundError:
            try:
                table.create_entity(
                    {"PartitionKey": "ratelimit", "RowKey": row_key,
                     "WindowStarted": now, "Failures": 1}
                )
                return
            except ResourceModifiedError:
                continue
        except ResourceModifiedError:
            continue
        except HttpResponseError as exc:
            raise InviteUnavailableError("Invite verification is temporarily unavailable.") from exc


def clear_failed_logins(client_ip: str) -> None:
    try:
        invite_table().delete_entity("ratelimit", _client_key(client_ip))
    except ResourceNotFoundError:
        pass
    except HttpResponseError as exc:
        raise InviteUnavailableError("Invite verification is temporarily unavailable.") from exc
