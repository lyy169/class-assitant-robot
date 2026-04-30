"""V2 auth, role, admin, and teacher API routes."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from .config import settings
from .security import create_access_token, decode_access_token, hash_password, verify_password


router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str = Field(..., min_length=6)
    role: str = "teacher"
    classroom_id: Optional[str] = None
    classroom_name: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str


AUTH_COOKIE_NAME = "auth_token"


def _database_url() -> str:
    database_url = settings.database_url.strip()
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL database URL is required for V2 auth APIs",
        )
    return database_url


def _connect():
    return psycopg2.connect(_database_url())


def _get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with _connect() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    user_id::text AS user_id,
                    username,
                    display_name,
                    password_hash,
                    role,
                    is_active
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None


def _get_user_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    with _connect() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    user_id::text AS user_id,
                    username,
                    display_name,
                    role,
                    is_active
                FROM users
                WHERE user_id::text = %s
                """,
                (str(user_id),),
            )
            row = cursor.fetchone()
            return dict(row) if row else None


def _user_public(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": str(user.get("user_id") or ""),
        "username": user.get("username") or "",
        "display_name": user.get("display_name") or user.get("username") or "",
        "role": user.get("role") or "",
    }


def _token_from_inputs(auth_token: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if auth_token:
        return auth_token
    if authorization and authorization.startswith("Bearer "):
        return authorization[len("Bearer "):].strip()
    return None


def _user_from_token(token: str) -> Dict[str, Any]:
    payload = decode_access_token(token)
    user = _get_user_by_user_id(str(payload["sub"]))
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid user")
    return _user_public(user)


def _get_current_user(
    auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    token = _token_from_inputs(auth_token, authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing auth token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user_from_token(token)


def _optional_current_user(
    auth_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    token = _token_from_inputs(auth_token, authorization)
    if not token:
        return None
    try:
        return _user_from_token(token)
    except Exception:
        return None


def _require_admin(current_user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    return current_user


def _require_teacher(current_user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
    if current_user.get("role") not in {"teacher", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="teacher role required")
    return current_user


def require_page_user(
    auth_token: Optional[str],
    required_role: Optional[str] = None,
) -> Dict[str, Any]:
    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login required")
    user = _user_from_token(auth_token)
    if required_role == "admin" and user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    if required_role == "teacher" and user.get("role") not in {"teacher", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="teacher role required")
    return user


def optional_page_user(auth_token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not auth_token:
        return None
    try:
        return _user_from_token(auth_token)
    except Exception:
        return None


@router.post("/auth/login")
def login(request: LoginRequest, response: Response) -> Dict[str, Any]:
    user = _get_user_by_username(request.username)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    token = create_access_token(
        subject=str(user["user_id"]),
        claims={"username": user["username"], "role": user["role"]},
    )
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )
    public_user = _user_public(user)
    return {
        "success": True,
        "user": public_user,
        "redirect_to": "/admin" if public_user["role"] == "admin" else "/teacher",
    }


@router.get("/auth/me")
def current_user(current_user: Dict[str, Any] = Depends(_get_current_user)) -> Dict[str, Any]:
    return {"success": True, "user": current_user}


@router.post("/auth/logout")
def logout(response: Response) -> Dict[str, Any]:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"success": True}


@router.post("/admin/users")
def create_user(request: UserCreateRequest, _: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    if request.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=422, detail="role must be teacher or admin")

    with _connect() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO users (user_id, username, password_hash, role, display_name)
                VALUES (%s::uuid, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    display_name = EXCLUDED.display_name,
                    is_active = TRUE
                RETURNING user_id::text AS user_id, username, display_name, role, is_active, created_at
                """,
                (str(uuid.uuid4()), request.username, hash_password(request.password), request.role, request.username),
            )
            user = dict(cursor.fetchone())
            if request.classroom_id:
                cursor.execute(
                    """
                    INSERT INTO teacher_classrooms (user_id, classroom_id, classroom_name)
                    VALUES (%s::uuid, %s, %s)
                    ON CONFLICT (user_id, classroom_id) DO UPDATE SET
                        classroom_name = EXCLUDED.classroom_name
                    """,
                    (
                        user["user_id"],
                        request.classroom_id,
                        request.classroom_name or request.classroom_id,
                    ),
                )
    return {"success": True, "user": user}


@router.get("/admin/users")
def list_users(_: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    with _connect() as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT u.user_id::text AS user_id, u.username, u.display_name, u.role, u.is_active, u.created_at,
                       COALESCE(json_agg(tc.classroom_id) FILTER (WHERE tc.classroom_id IS NOT NULL), '[]') AS classrooms
                FROM users u
                LEFT JOIN teacher_classrooms tc ON tc.user_id = u.user_id
                GROUP BY u.user_id, u.username, u.display_name, u.role, u.is_active, u.created_at
                ORDER BY u.created_at
                """
            )
            users = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "users": users}


@router.get("/teacher/sessions")
def teacher_sessions(current_user: Dict[str, Any] = Depends(_require_teacher)) -> Dict[str, Any]:
    from .main import repository

    sessions = repository.get_teacher_sessions(current_user["user_id"])
    return {"success": True, "sessions": sessions}


@router.get("/teacher/sessions/{analysis_id}")
def teacher_session_detail(
    analysis_id: str,
    current_user: Dict[str, Any] = Depends(_require_teacher),
) -> Dict[str, Any]:
    from .main import repository

    if hasattr(repository, "get_teacher_session_detail"):
        session = repository.get_teacher_session_detail(
            current_user["user_id"],
            analysis_id,
            is_admin=current_user.get("role") == "admin",
        )
    else:
        session = None
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    return {"success": True, "session": session}


@router.get("/teacher/trends")
def teacher_trends(
    limit: int = Query(default=5, ge=1, le=50),
    current_user: Dict[str, Any] = Depends(_require_teacher),
) -> Dict[str, Any]:
    from .main import repository

    if hasattr(repository, "get_teacher_trends"):
        trends = repository.get_teacher_trends(current_user["user_id"], limit=limit)
    else:
        trends = []
    return {"success": True, "limit": limit, "trends": trends}


@router.get("/teacher/results/recent")
def teacher_results_recent(
    limit: int = Query(default=10, ge=1, le=100),
    classroom_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(_require_teacher),
) -> Dict[str, Any]:
    from .main import repository

    if status not in (None, "", "raw", "reviewed", "archived"):
        raise HTTPException(status_code=400, detail="status must be raw, reviewed, or archived")
    if not hasattr(repository, "get_workbench_recent"):
        return {
            "success": True,
            "limit": limit,
            "classroom_id": classroom_id,
            "status": status,
            "fallback_to_sample": False,
            "items": [],
        }
    user_id = current_user["user_id"] if current_user.get("role") == "teacher" else None
    items = repository.get_workbench_recent(limit=limit, classroom_id=classroom_id, status=status, user_id=user_id)
    return {
        "success": True,
        "limit": limit,
        "classroom_id": classroom_id,
        "status": status,
        "fallback_to_sample": False,
        "items": items,
    }


@router.get("/teacher/classrooms")
def teacher_classrooms(current_user: Dict[str, Any] = Depends(_require_teacher)) -> Dict[str, Any]:
    from .main import repository

    if not hasattr(repository, "get_workbench_classrooms"):
        return {"success": True, "items": []}
    user_id = current_user["user_id"] if current_user.get("role") == "teacher" else None
    return {"success": True, "items": repository.get_workbench_classrooms(user_id=user_id)}


@router.get("/teacher/overview")
def teacher_overview(current_user: Dict[str, Any] = Depends(_require_teacher)) -> Dict[str, Any]:
    from .main import repository

    user_id = current_user["user_id"] if current_user.get("role") == "teacher" else None
    if not hasattr(repository, "get_teacher_overview"):
        return {
            "success": True,
            "teacher": {"id": None, "username": "demo_teacher", "display_name": "Demo Teacher", "role": "teacher"},
            "metrics": {
                "classroom_count": 0,
                "total_result_count": 0,
                "recent_result_count": 0,
                "raw_count": 0,
                "reviewed_count": 0,
                "archived_count": 0,
                "avg_feedback_score": None,
                "avg_attention_score": None,
                "avg_response_score": None,
            },
            "latest_results": [],
            "classroom_summaries": [],
            "todo_items": [],
        }
    return repository.get_teacher_overview(user_id=user_id)


def _parse_days(days: Optional[str]) -> Optional[int]:
    if days in (None, "", "all"):
        return None
    try:
        value = int(str(days))
    except ValueError:
        raise HTTPException(status_code=400, detail="days must be 7, 30, or all")
    if value <= 7:
        return 7
    if value <= 30:
        return 30
    return None


@router.get("/teacher/results")
def teacher_results(
    classroom_id: Optional[str] = None,
    status: Optional[str] = None,
    days: Optional[str] = Query(default="30"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: Dict[str, Any] = Depends(_require_teacher),
) -> Dict[str, Any]:
    from .main import repository

    if status not in (None, "", "raw", "reviewed", "archived"):
        raise HTTPException(status_code=400, detail="status must be raw, reviewed, or archived")
    parsed_days = _parse_days(days)
    user_id = current_user["user_id"] if current_user.get("role") == "teacher" else None
    if not hasattr(repository, "get_teacher_results"):
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "status": status or "",
                "days": parsed_days,
                "limit": limit,
                "offset": offset,
            },
            "items": [],
            "total": 0,
        }
    return repository.get_teacher_results(
        user_id=user_id,
        classroom_id=classroom_id,
        status=status,
        days=parsed_days,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/overview")
def admin_overview(_: Dict[str, Any] = Depends(_require_admin)) -> Dict[str, Any]:
    from .main import repository

    if not hasattr(repository, "get_admin_overview"):
        return {
            "success": True,
            "admin": {"id": None, "username": "demo_admin", "display_name": "Demo Admin", "role": "admin"},
            "metrics": {
                "teacher_count": 0,
                "classroom_count": 0,
                "result_count": 0,
                "recent_result_count": 0,
                "today_result_count": 0,
                "raw_count": 0,
                "reviewed_count": 0,
                "archived_count": 0,
                "avg_feedback_score": None,
                "avg_attention_score": None,
                "avg_response_score": None,
            },
            "system_status": {
                "cloud_service": "ok",
                "database": "unavailable",
                "latest_upload_at": None,
                "latest_raw_path": "",
                "latest_analysis_id": "",
            },
            "status_distribution": {"raw": 0, "reviewed": 0, "archived": 0},
            "latest_results": [],
            "quick_links": [],
        }
    return repository.get_admin_overview()


@router.get("/admin/classrooms")
def admin_classrooms(
    q: Optional[str] = None,
    teacher_id: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    from .main import repository

    if not hasattr(repository, "get_admin_classrooms"):
        return {"success": True, "overview": {}, "items": [], "total": 0}
    return repository.get_admin_classrooms(q=q, teacher_id=teacher_id, limit=limit, offset=offset)


@router.get("/admin/teachers")
def admin_teachers(
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    from .main import repository

    if not hasattr(repository, "get_admin_teachers"):
        return {"success": True, "overview": {}, "items": [], "total": 0}
    return repository.get_admin_teachers(q=q, limit=limit, offset=offset)


@router.get("/admin/results")
def admin_results(
    classroom_id: Optional[str] = None,
    teacher_id: Optional[str] = None,
    status: Optional[str] = None,
    days: Optional[str] = Query(default="30"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    from .main import repository

    if status not in (None, "", "raw", "reviewed", "archived"):
        raise HTTPException(status_code=400, detail="status must be raw, reviewed, or archived")
    parsed_days = _parse_days(days)
    if not hasattr(repository, "get_admin_results"):
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "teacher_id": teacher_id or "",
                "status": status or "",
                "days": parsed_days,
                "limit": limit,
                "offset": offset,
            },
            "overview": {},
            "items": [],
            "total": 0,
        }
    return repository.get_admin_results(
        classroom_id=classroom_id,
        teacher_id=teacher_id,
        status=status,
        days=parsed_days,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/ingestion")
def admin_ingestion(
    classroom_id: Optional[str] = None,
    device_id: Optional[str] = None,
    source_host: Optional[str] = None,
    days: Optional[str] = Query(default="30"),
    limit: int = Query(default=20, ge=1, le=100),
    _: Dict[str, Any] = Depends(_require_admin),
) -> Dict[str, Any]:
    from .main import repository

    parsed_days = _parse_days(days)
    if not hasattr(repository, "get_admin_ingestion"):
        return {
            "success": True,
            "filters": {
                "classroom_id": classroom_id or "",
                "device_id": device_id or "",
                "source_host": source_host or "",
                "days": parsed_days,
                "limit": limit,
            },
            "overview": {},
            "pipeline": [],
            "devices": [],
            "recent_ingestions": [],
            "video_summary": {"playable": 0, "pending": 0, "missing": 0, "unknown": 0},
            "validation_hints": [],
        }
    return repository.get_admin_ingestion(
        classroom_id=classroom_id,
        device_id=device_id,
        source_host=source_host,
        days=parsed_days,
        limit=limit,
    )


@router.get("/teacher/results/{result_id}")
def teacher_result_detail(result_id: str, current_user: Dict[str, Any] = Depends(_require_teacher)) -> Dict[str, Any]:
    from .main import repository

    if not hasattr(repository, "get_workbench_result_detail"):
        raise HTTPException(status_code=404, detail="result not found")
    user_id = current_user["user_id"] if current_user.get("role") == "teacher" else None
    result = repository.get_workbench_result_detail(result_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="result not found")
    return {"success": True, "result": result}


@router.patch("/teacher/results/{result_id}/status")
def teacher_result_status(
    result_id: str,
    request: StatusUpdateRequest,
    current_user: Dict[str, Any] = Depends(_require_teacher),
) -> Dict[str, Any]:
    from .main import repository

    if request.status not in {"raw", "reviewed", "archived"}:
        raise HTTPException(status_code=400, detail="status must be raw, reviewed, or archived")
    if not hasattr(repository, "update_workbench_status"):
        raise HTTPException(status_code=404, detail="result not found")
    user_id = current_user["user_id"] if current_user.get("role") == "teacher" else None
    result = repository.update_workbench_status(result_id, request.status, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="result not found")
    return {"success": True, "result": result}
