# V2 Phase 2.9 Spec: Auth, Role Routing, And Permission Boundary

## 1. Purpose

Phase 2.9 upgrades the cloud dashboard from demo/default access into a role-aware platform.

The target is:

```text
competition-ready login experience
  + real auth data structures
  + teacher/admin role routing
  + classroom-scoped teacher visibility
  + admin global visibility
```

This phase should be suitable for competition demonstration while preserving a path toward a production-grade account system.

## 2. Confirmed Scope

In scope:

- unified login page
- teacher/admin role routing
- auth database schema
- seeded demo users
- HttpOnly cookie login state
- page route protection
- teacher API classroom filtering
- admin API role protection
- dashboard result permission check
- logout
- validation script

Out of scope:

- registration
- password reset
- OAuth or social login
- multi-school / multi-tenant model
- complex RBAC
- button-level permissions
- admin user-management UI
- classroom-management UI
- upload API device token
- Raspberry Pi or local analyzer changes
- video asset permission model

## 3. Roles

Supported roles:

```text
teacher
admin
```

Do not add:

```text
student
parent
guest
school_admin
super_admin
```

## 4. Database Design

Add:

```text
users
teacher_classrooms
```

Do not add:

```text
admins
teachers
classrooms
permissions
roles
schools
login_sessions
```

Admins and teachers are both records in `users`; their behavior is determined by `users.role`.

### 4.1 `users`

Recommended schema:

```sql
CREATE TABLE IF NOT EXISTS users (
  user_id UUID PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('teacher', 'admin')),
  display_name TEXT NOT NULL,
  email TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);
```

### 4.2 `teacher_classrooms`

Recommended schema:

```sql
CREATE TABLE IF NOT EXISTS teacher_classrooms (
  id UUID PRIMARY KEY,
  teacher_user_id UUID NOT NULL REFERENCES users(user_id),
  classroom_id TEXT NOT NULL,
  classroom_name TEXT,
  role_in_classroom TEXT NOT NULL DEFAULT 'owner',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (teacher_user_id, classroom_id)
);
```

### 4.3 Seed Users

Seed demo users:

```text
admin / admin123 / role=admin
teacher / teacher123 / role=teacher / classroom_101
```

Passwords must be hashed. Do not store plaintext passwords.

## 5. Auth APIs

Add or confirm:

```text
POST /api/auth/login
GET /api/auth/me
POST /api/auth/logout
```

### 5.1 Login

Request:

```json
{
  "username": "teacher",
  "password": "teacher123"
}
```

Success:

```json
{
  "success": true,
  "user": {
    "user_id": "uuid",
    "username": "teacher",
    "display_name": "Demo Teacher",
    "role": "teacher"
  },
  "redirect_to": "/teacher"
}
```

Failure:

```json
{
  "success": false,
  "message": "Invalid username or password"
}
```

### 5.2 Current User

Authenticated:

```json
{
  "success": true,
  "authenticated": true,
  "user": {
    "user_id": "uuid",
    "username": "teacher",
    "display_name": "Demo Teacher",
    "role": "teacher"
  }
}
```

Unauthenticated:

```json
{
  "success": false,
  "authenticated": false
}
```

### 5.3 Logout

Response:

```json
{
  "success": true
}
```

## 6. Login State

Use:

```text
JWT in HttpOnly cookie
```

Cookie:

```text
auth_token
HttpOnly
SameSite=Lax
Path=/
```

Do not require `Secure` while running the current HTTP-only competition environment. Add it later when HTTPS is available.

JWT payload should include:

```text
sub=user_id
username
role
exp
```

Recommended expiry:

```text
24 hours
```

## 7. Page Routing

### 7.1 Root

```text
GET /
```

Rules:

```text
not logged in -> /login
teacher -> /teacher
admin -> /admin
```

### 7.2 Login

```text
GET /login
```

Rules:

```text
not logged in -> render login page
teacher -> /teacher
admin -> /admin
```

### 7.3 Teacher Pages

Protect:

```text
/teacher
/teacher/results
```

Rules:

```text
require login
teacher role required
```

### 7.4 Admin Pages

Protect:

```text
/admin
/admin/classrooms
/admin/teachers
/admin/results
/admin/ingestion
```

Rules:

```text
admin only
```

### 7.5 Dashboard

Protect:

```text
/dashboard?result_id=...
```

Rules:

```text
require login
admin -> can view all results
teacher -> result classroom_id must belong to teacher_classrooms
```

## 8. API Permissions

### 8.1 Teacher APIs

Teacher API routes may be used by both teacher and admin.

Rules:

```text
teacher -> filter by teacher_classrooms
admin -> global view
```

Apply to:

```text
/api/teacher/overview
/api/teacher/results
/api/teacher/results/recent
/api/teacher/classrooms
/api/teacher/results/{result_id}
/api/teacher/results/{result_id}/status
```

### 8.2 Admin APIs

Rules:

```text
admin only
```

Apply to:

```text
/api/admin/overview
/api/admin/classrooms
/api/admin/teachers
/api/admin/results
/api/admin/ingestion
```

### 8.3 Upload API

Keep unchanged in Phase 2.9:

```text
POST /api/interaction-results
```

Do not require login or user cookie for the upload API in this phase.

Reason:

```text
The Raspberry Pi -> local analyzer -> cloud upload path was just stabilized in Phase 2.8.1. Device upload credentials should be designed separately later.
```

## 9. Frontend Requirements

### 9.1 Login Page

Add:

```text
/login
```

Required UI:

- system name
- three-side chain message: Raspberry Pi capture -> local analysis -> cloud feedback
- username field
- password field
- login button
- teacher demo login button
- admin demo login button
- error message area

Demo buttons must call the real login API; they must not bypass auth.

### 9.2 User Bar

Teacher/admin/dashboard pages should show:

```text
display_name
role
logout action
```

### 9.3 403 Page

Provide a simple 403 response/page for authenticated users without permission.

## 10. Compatibility

Preserve:

- Phase 2.5 dashboard behavior after login
- Phase 2.6 teacher home/results after login
- Phase 2.7 admin pages after login
- Phase 2.8 admin ingestion after login
- Phase 2.8.1 upload and ingestion metadata flow

