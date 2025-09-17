# Guide for jwt Auth RBAC Implementation

# **1) Install**



```
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] pydantic-settings
```



# **2) Minimal working example (single file)**





Save as app.py and run uvicorn app:app --reload.

```
from datetime import datetime, timedelta
from typing import Annotated, Dict, List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, BaseSettings

# -----------------------------
# Settings & Security primitives
# -----------------------------
class Settings(BaseSettings):
    JWT_SECRET: str = "change-me"   # use strong env secret in prod
    JWT_ALG: str = "HS256"
    ACCESS_TTL_MIN: int = 30

settings = Settings()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2 = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={  # optional: expose scopes in OpenAPI
        "projects:read": "Read projects",
        "projects:write": "Create/update projects",
        "admin": "Admin-level operations"
    },
)

# -----------------------------
# Fake user store (replace w/ DB)
# -----------------------------
# Roles → permissions
ROLE_PERMS: Dict[str, List[str]] = {
    "viewer": ["projects:read"],
    "editor": ["projects:read", "projects:write"],
    "admin":  ["projects:read", "projects:write", "admin"],
}

class User(BaseModel):
    username: str
    hashed_password: str
    roles: List[str]

# demo users
FAKE_USERS: Dict[str, User] = {
    "alice": User(username="alice", hashed_password=pwd_ctx.hash("alicepw"), roles=["viewer"]),
    "bob":   User(username="bob",   hashed_password=pwd_ctx.hash("bobpw"),   roles=["editor"]),
    "root":  User(username="root",  hashed_password=pwd_ctx.hash("rootpw"),  roles=["admin"]),
}

def get_user(username: str) -> Optional[User]:
    return FAKE_USERS.get(username)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

# -----------------------------
# JWT helpers
# -----------------------------
def create_access_token(sub: str, roles: List[str], perms: List[str]) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TTL_MIN)).timestamp()),
        "roles": roles,
        "perms": perms,  # flatten for fast checks
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    roles: List[str] = []
    perms: List[str] = []

# -----------------------------
# Auth dependency (scopes/RBAC)
# -----------------------------
async def get_current_user(security_scopes: SecurityScopes, token: Annotated[str, Depends(oauth2)]) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        payload = TokenPayload(sub=data.get("sub"), roles=data.get("roles", []), perms=data.get("perms", []))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = get_user(payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # If endpoint declares scopes, ensure token has them (via perms)
    for scope in security_scopes.scopes:
        if scope not in payload.perms:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {scope}",
            )
    return user

# Optional convenience checker for roles
def require_roles(*required: str):
    async def checker(user: Annotated[User, Depends(get_current_user)]):
        if not set(required).issubset(set(user.roles)):
            raise HTTPException(status_code=403, detail=f"Requires roles: {required}")
        return user
    return checker

# -----------------------------
# API
# -----------------------------
app = FastAPI(title="JWT RBAC Demo")

@app.post("/auth/token", response_model=TokenResponse, tags=["auth"])
async def issue_token(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    OAuth2 password flow: username/password → JWT.
    Roles & permissions embedded in the token for quick checks.
    """
    user = get_user(form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Bad credentials")

    # Build permission set from roles
    perms: List[str] = sorted({p for r in user.roles for p in ROLE_PERMS.get(r, [])})
    token = create_access_token(sub=user.username, roles=user.roles, perms=perms)
    return TokenResponse(access_token=token)

# Open to any authenticated user
@app.get("/me", tags=["me"])
async def me(user: Annotated[User, Depends(get_current_user)]):
    return {"username": user.username, "roles": user.roles}

# Requires a permission (scope) via OAuth2 / SecurityScopes
@app.get("/projects", tags=["projects"])
async def list_projects(user: Annotated[User, Security(get_current_user, scopes=["projects:read"])]):
    return [{"id": 1, "name": "Demo"}]

# Requires editor/admin permissions
@app.post("/projects", tags=["projects"])
async def create_project(user: Annotated[User, Security(get_current_user, scopes=["projects:write"])]):
    return {"status": "created"}

# Example role guard (admin only)
@app.get("/admin/metrics", tags=["admin"])
async def admin_metrics(user: Annotated[User, Depends(require_roles("admin"))]):
    return {"uptime": "ok"}
```



### **How it works**





- **Login**: POST /auth/token with username, password (form fields per OAuth2).

- **Token contents**: sub, roles, and a flattened perms list derived from roles.

- **Protect endpoints**:

  

  - Permission (scope) based: Security(get_current_user, scopes=["projects:write"])
  - Role based: Depends(require_roles("admin"))

  







# **3) Recommended structure (when you split files)**



```
app/
  core/config.py          # Settings
  core/security.py        # hash/verify, create/verify JWT
  models/user.py          # ORM + Pydantic
  rbac/policy.py          # ROLE_PERMS + helpers
  deps/auth.py            # get_current_user, require_roles
  routers/auth.py         # /auth/token
  routers/projects.py     # sample protected routes
  main.py                 # FastAPI app include_router(...)
```



# **4) Best-practice notes (prod hardening)**





- **Secret management**: load JWT_SECRET from environment/secret manager; rotate periodically.
- **Algorithms**: HS256 is fine with strong secret; prefer **RS256/EdDSA** with key pairs if you’ll validate in multiple services.
- **Token lifetime**: short-lived access tokens (e.g., 15–30 min) + **refresh tokens** (httpOnly cookie, rotation, reuse-detection).
- **Revocation**: maintain a token-id (jti) blacklist/allowlist (e.g., Redis) for logout/compromise.
- **Scopes vs roles**: keep **roles → permissions** mapping in code or DB; authorize **by permission** at endpoints.
- **Transport**: require HTTPS; if using cookies, set Secure, HttpOnly, SameSite=strict|lax.
- **Multi-tenant**: include tenant_id claim and validate against route/resource.
- **Auditing**: add aud, iss, jti, and log authz decisions.
- **OpenAPI**: document scopes via OAuth2PasswordBearer(scopes=...) (already shown).
- **Testing**: unit-test create_access_token, get_current_user, and each guard; add integration tests for protected routes.







# **5) Quick curl test**



```
# login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=bob&password=bobpw" -H "Content-Type: application/x-www-form-urlencoded" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# access endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/projects       # OK for editor
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/projects  # OK for editor
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/admin/metrics     # 403 (bob lacks admin)
```

---

# copy-pasteable snippets to implement JWT RBAC in FastAPI for these roles:



- **super_admin** (seeded directly in DB)
- **admin** (can create & manage non-admin users)
- **recruiter**
- **candidate**





No public signup: **admins** create users; only **super_admin** can grant/revoke **admin**.



------





# **0) Packages**



```
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] pydantic-settings sqlalchemy alembic email-validator
```



------





# **1) Data model (SQLAlchemy)**





Minimal, production-ready shape with invites and role mapping. Add tenant_id if you’re multi-tenant.

```
# app/models.py
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)  # super_admin, admin, recruiter, candidate

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    user: Mapped[User] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship()

class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role_name: Mapped[str] = mapped_column(String(50))  # desired initial role
    code_jti: Mapped[str] = mapped_column(String(64), unique=True)  # to prevent reuse
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    __table_args__ = (UniqueConstraint("email", "used_at", name="uniq_open_invite_per_email"),)
```

Create an Alembic migration for the above (or Base.metadata.create_all for a quick start).



------





# **2) Seed roles & Super-Admin**





Run once (migration seed or script):

```
# scripts/seed.py
from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.models import Base, Role, User, UserRole

engine = create_engine("postgresql+psycopg://user:pass@localhost/db")  # update
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

with Session(engine) as s:
    for r in ("super_admin","admin","recruiter","candidate"):
        if not s.scalar(select(Role).where(Role.name==r)):
            s.add(Role(name=r))
    s.commit()

    email = "owner@yourco.com"
    if not s.scalar(select(User).where(User.email==email)):
        u = User(email=email, password_hash=pwd.hash("ChangeMe!Long+Random"), is_active=True)
        s.add(u); s.flush()
        super_admin = s.scalar(select(Role).where(Role.name=="super_admin"))
        s.add(UserRole(user_id=u.id, role_id=super_admin.id))
        s.commit()
```

> Change the password immediately in production.



------





# **3) Settings & security helpers**



```
# app/security.py
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, BaseSettings

class Settings(BaseSettings):
    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    ACCESS_TTL_MIN: int = 30
    INVITE_TTL_HOURS: int = 48

settings = Settings()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str: return pwd_ctx.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd_ctx.verify(p, h)

class TokenData(BaseModel):
    sub: str
    roles: list[str]
    jti: str | None = None

def _encode(payload: dict, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload |= {"iat": int(now.timestamp()), "exp": int((now + ttl).timestamp())}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def create_access_token(email: str, roles: list[str]) -> str:
    return _encode({"sub": email, "roles": roles}, timedelta(minutes=settings.ACCESS_TTL_MIN))

def create_invite_token(email: str, role: str, jti: str) -> str:
    return _encode({"sub": email, "role": role, "type": "invite", "jti": jti},
                   timedelta(hours=settings.INVITE_TTL_HOURS))

def decode_token(t: str) -> dict:
    return jwt.decode(t, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
```



------





# **4) RBAC policy & guards**





- **Hierarchy** (who can manage whom): super_admin > admin > recruiter > candidate
- **Rule**: A user can only assign roles **strictly below** their highest role; only **super_admin** may assign **admin**.



```
# app/rbac.py
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError
from app.security import decode_token
from app.db import get_user_by_email  # implement with SQLAlchemy

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")

ROLE_ORDER = {
    "super_admin": 100,
    "admin": 80,
    "recruiter": 50,
    "candidate": 20,
}

def highest_role(roles: list[str]) -> str:
    return sorted(roles, key=lambda r: ROLE_ORDER.get(r, 0), reverse=True)[0] if roles else "candidate"

async def get_current_identity(token: str = Depends(oauth2)) -> dict:
    try:
        data = decode_token(token)
        email = data.get("sub")
        roles = data.get("roles", [])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not email: raise HTTPException(status_code=401, detail="Invalid token (no sub)")
    user = await get_user_by_email(email)  # must check is_active
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    # optional: re-load roles from DB instead of trusting token
    return {"email": email, "roles": roles or [ur.role.name for ur in user.roles], "user": user}

def require_roles(*allowed: str):
    async def dep(ctx = Depends(get_current_identity)):
        user_roles = set(ctx["roles"])
        if not (user_roles & set(allowed)):
            raise HTTPException(status_code=403, detail=f"Requires one of roles: {allowed}")
        return ctx
    return dep

def can_assign(granter_roles: list[str], target_role: str) -> bool:
    gmax = highest_role(granter_roles)
    return ROLE_ORDER[gmax] > ROLE_ORDER.get(target_role, 0) and not (
        target_role == "admin" and gmax != "super_admin"
    )
```



------





# **5) Auth router (login + activate via invite)**





- **Login**: username/password → JWT
- **Invite**: admin creates an invite → email link carries invite token (JWT with type=invite)
- **Activate**: invited user sets password (no public signup page); consumes invite



```
# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from app.security import create_access_token, verify_password, hash_password, create_invite_token
from app.models import User, Role, UserRole, Invite
from app.rbac import get_current_identity, require_roles, can_assign
from app.db import get_db, get_user_with_roles, get_role_by_name  # implement

router = APIRouter(prefix="/auth", tags=["auth"])

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/token", response_model=TokenOut)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_with_roles(db, form.username)
    if not user or not verify_password(form.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Bad credentials")
    roles = [ur.role.name for ur in user.roles]
    return TokenOut(access_token=create_access_token(user.email, roles))

class InviteCreateIn(BaseModel):
    email: EmailStr
    role: str  # recruiter | candidate | (admin only if super_admin)

class InviteOut(BaseModel):
    invite_token: str

@router.post("/invite", response_model=InviteOut, dependencies=[Depends(require_roles("admin","super_admin"))])
def create_invite(payload: InviteCreateIn, ctx=Depends(get_current_identity), db: Session = Depends(get_db)):
    if not can_assign(ctx["roles"], payload.role):
        raise HTTPException(status_code=403, detail="You cannot assign this role")
    jti = uuid4().hex
    inv = Invite(email=payload.email, role_name=payload.role, code_jti=jti,
                 expires_at=datetime.now(timezone.utc).replace(microsecond=0) + \
                            (datetime.utcnow() - datetime.utcnow())  # dummy to satisfy type
                 )
    # proper expires_at:
    from datetime import timedelta
    inv.expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    inv.created_by_user_id = ctx["user"].id
    db.add(inv); db.commit()
    token = create_invite_token(payload.email, payload.role, jti)
    # send token by email in real life
    return InviteOut(invite_token=token)

class ActivateIn(BaseModel):
    invite_token: str
    password: str

@router.post("/activate", response_model=TokenOut)
def activate(body: ActivateIn, db: Session = Depends(get_db)):
    from jose import JWTError
    from app.security import decode_token
    try:
        data = decode_token(body.invite_token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid invite token")
    if data.get("type") != "invite": raise HTTPException(status_code=400, detail="Wrong token type")
    email, role, jti = data["sub"], data["role"], data["jti"]

    inv: Invite | None = db.query(Invite).filter(Invite.code_jti==jti).one_or_none()
    if not inv or inv.used_at is not None or inv.email.lower()!=email.lower():
        raise HTTPException(status_code=400, detail="Invite not found or used")
    if inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite expired")

    # Create user (or set password if existing & inactive)
    user = db.query(User).filter(User.email==email).one_or_none()
    if user is None:
        user = User(email=email, password_hash=hash_password(body.password), is_active=True)
        db.add(user); db.flush()
        r = get_role_by_name(db, role)
        db.add(UserRole(user_id=user.id, role_id=r.id))
    else:
        user.password_hash = hash_password(body.password)
        user.is_active = True
    inv.used_at = datetime.now(timezone.utc)
    db.commit()

    roles = [ur.role.name for ur in user.roles]
    return TokenOut(access_token=create_access_token(user.email, roles))
```



------





# **6) Admin-only user management**





- **Only super_admin** can grant/revoke **admin**.
- **admin** can manage **recruiter/candidate**.



```
# app/routers/admin_users.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.rbac import require_roles, get_current_identity, can_assign
from app.models import User, Role, UserRole
from app.db import get_db, get_user_with_roles, get_role_by_name

router = APIRouter(prefix="/admin/users", tags=["admin:users"], dependencies=[Depends(require_roles("admin","super_admin"))])

class AssignRoleIn(BaseModel):
    role: str

@router.post("/{email}/assign-role")
def assign_role(email: EmailStr, body: AssignRoleIn, ctx=Depends(get_current_identity), db: Session = Depends(get_db)):
    if not can_assign(ctx["roles"], body.role):
        raise HTTPException(status_code=403, detail="You cannot assign this role")
    user = get_user_with_roles(db, email)
    if not user: raise HTTPException(status_code=404, detail="User not found")

    # if assigning admin and granter is not super_admin → blocked by can_assign already
    target_role = get_role_by_name(db, body.role)
    has_it = any(ur.role_id == target_role.id for ur in user.roles)
    if not has_it:
        db.add(UserRole(user_id=user.id, role_id=target_role.id))
        db.commit()
    return {"ok": True}

@router.post("/{email}/deactivate")
def deactivate_user(email: EmailStr, ctx=Depends(get_current_identity), db: Session = Depends(get_db)):
    # optional: prevent deactivating same-or-higher roles
    target = get_user_with_roles(db, email)
    if not target: raise HTTPException(status_code=404, detail="User not found")
    target.is_active = False
    db.commit()
    return {"ok": True}
```



------





# **7) Example domain routers (guards in action)**



```
# app/routers/jobs.py
from fastapi import APIRouter, Depends
from app.rbac import require_roles

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", dependencies=[Depends(require_roles("admin","recruiter"))])
def list_jobs(): return [{"id":1,"title":"Backend Engineer"}]

@router.post("", dependencies=[Depends(require_roles("admin","recruiter"))])
def create_job(): return {"status":"created"}

@router.get("/my-applications", dependencies=[Depends(require_roles("candidate"))])
def my_apps(): return [{"job_id":1,"status":"submitted"}]
```



------





# **8) Wire the app**



```
# app/main.py
from fastapi import FastAPI
from app.routers import auth, admin_users, jobs

app = FastAPI(title="Recruiting RBAC")

app.include_router(auth.router)
app.include_router(admin_users.router)
app.include_router(jobs.router)
```

Run:

```
uvicorn app.main:app --reload
```



------





# **9) Flow summary (end-to-end)**





1. **Seed** roles + **super_admin** in DB (Step 2).

2. **super_admin** logs in → gets JWT.

3. **super_admin** can:

   

   - Invite **admin** (POST /auth/invite {email, role:"admin"}).
   - Assign/revoke **admin** via /admin/users/{email}/assign-role (only super_admin passes can_assign).

   

4. **admin** logs in → JWT.

5. **admin** can invite **recruiter** or **candidate** via /auth/invite.

6. Invited user opens **activation** UI → calls /auth/activate {invite_token, password} → account created/activated, JWT returned.

7. Domain routes check **roles**:

   

   - Recruiter: manage jobs.
   - Candidate: view “my applications”.
   - Admin: everything except super_admin-only ops (e.g., granting admin).

   





------





# **10) Critical policies you now enforce**





- **No public signup** (only /auth/activate with a valid invite).
- **Privilege ceiling**: can_assign() prevents lateral/elevated grants.
- **Deactivation**: soft lock via is_active (auth rejects).
- **JWT** includes role list; you may re-load roles from DB in get_current_identity for stronger security.





------





# **11) Tests you should add (short list)**





- Login success/fail, inactive user → 401

- Invite creation:

  

  - admin → recruiter/candidate ✅
  - admin → admin ❌
  - super_admin → admin ✅

  

- Invite redeem:

  

  - wrong/expired/used token ❌
  - success sets password & role ✅

  

- Route protection:

  

  - candidate cannot POST /jobs ❌
  - recruiter/admin can ✅

  





------

# Password changes

Let’s add two flows on top of your RBAC design:



1. **Force password change on first login** (or after an admin-issued temporary password)
2. **Admin-initiated password reset** when a user loses access





Below are drop-in changes and new endpoints for your existing FastAPI+JWT RBAC scaffold.



------





# **1) DB changes**





Add two tables/columns:

```
# app/models.py  (additions)

from sqlalchemy import Text

class User(Base):
    __tablename__ = "users"
    # ... existing fields ...
    must_change_password: Mapped[bool] = mapped_column(default=False)   # new
    last_password_change_at: Mapped[datetime | None] = mapped_column(nullable=True)  # new

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Rules**



- When a user is created via **invite + self-set password** → must_change_password=False.
- When an **admin** sets/overrides a user password (e.g., recovery) → must_change_password=True.
- After any successful user-initiated change → set last_password_change_at=now, must_change_password=False.





------





# **2) Security helpers (tokens for reset)**





Add reset token helpers:

```
# app/security.py  (additions)

def create_reset_token(email: str, jti: str) -> str:
    # keep resets short-lived (e.g., 30–60 min)
    return _encode({"sub": email, "type": "reset", "jti": jti}, timedelta(minutes=60))
```



------





# **3) Enforce “must change password” at login / route access**







## **A) On login response**





Return a flag so the UI can prompt immediately.

```
# app/routers/auth.py  (adjust /auth/token)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False   # new

@router.post("/token", response_model=TokenOut)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_with_roles(db, form.username)
    if not user or not verify_password(form.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Bad credentials")
    roles = [ur.role.name for ur in user.roles]
    return TokenOut(
        access_token=create_access_token(user.email, roles),
        must_change_password=bool(user.must_change_password),
    )
```



## **B) Server-side enforcement (can’t rely on UI alone)**





Block protected routes until password is changed. Keep /auth/change-password and /auth/reset/confirm open to authenticated users with the flag.



Create a tiny guard:

```
# app/rbac.py  (add)
from fastapi import Request

def require_password_fresh():
    async def dep(ctx = Depends(get_current_identity), request: Request = None):
        user = ctx["user"]
        # allow change/reset endpoints even if flag is set
        allowed_paths = {"/auth/change-password", "/auth/reset/confirm"}
        if user.must_change_password and request and request.url.path not in allowed_paths:
            raise HTTPException(
                status_code=403,
                detail="Password change required",
            )
        return ctx
    return dep
```

Use it alongside your role guards on any route that requires a “fresh” password (recommended for all authenticated business routes):

```
# app/routers/jobs.py
router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", dependencies=[Depends(require_password_fresh()), Depends(require_roles("admin","recruiter"))])
def list_jobs(): ...
```

(You can also apply require_password_fresh() globally by adding it to each router’s dependencies=[...] in main.py.)



------





# **4) User-initiated change on first login (and anytime)**



```
# app/routers/auth.py  (add)

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
def change_password(body: ChangePasswordIn, ctx=Depends(get_current_identity), db: Session = Depends(get_db)):
    user = ctx["user"]
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.last_password_change_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}
```

> This works for both:

> *a)* first login with temp password, and *b)* regular user-initiated change.



------





# **5) Admin-initiated password reset (lost password)**





Flow: **admin** requests a reset → server issues a short-lived *reset token* (emailed) → user opens reset UI and submits token + new password.

```
# app/routers/admin_users.py  (add endpoints)

from uuid import uuid4
from app.models import PasswordReset
from app.security import create_reset_token
from datetime import timedelta, timezone, datetime

class ResetRequestIn(BaseModel):
    email: EmailStr
    reason: str | None = None

class ResetRequestOut(BaseModel):
    reset_token: str  # In production, email this; return only for testing/dev

@router.post("/password-reset/request", response_model=ResetRequestOut)
def admin_password_reset_request(body: ResetRequestIn,
                                 ctx=Depends(get_current_identity),
                                 db: Session = Depends(get_db)):
    # Only admin or super_admin can trigger a reset
    roles = set(ctx["roles"])
    if not ({"admin","super_admin"} & roles):
        raise HTTPException(status_code=403, detail="Admin required")

    user = get_user_with_roles(db, body.email)
    if not user:  # optionally avoid leaking existence; still issue a no-op
        raise HTTPException(status_code=404, detail="User not found")

    jti = uuid4().hex
    pr = PasswordReset(
        email=body.email,
        jti=jti,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
        requested_by_user_id=ctx["user"].id,
        reason=body.reason
    )
    db.add(pr); db.commit()

    token = create_reset_token(body.email, jti)
    # TODO: send token by email (SES/SendGrid). For now, return for dev/testing:
    return ResetRequestOut(reset_token=token)
```

User completes the reset:

```
# app/routers/auth.py  (add)

class ResetConfirmIn(BaseModel):
    reset_token: str
    new_password: str

@router.post("/reset/confirm")
def reset_confirm(body: ResetConfirmIn, db: Session = Depends(get_db)):
    from jose import JWTError
    from app.security import decode_token

    try:
        data = decode_token(body.reset_token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if data.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Wrong token type")

    email, jti = data.get("sub"), data.get("jti")
    pr = db.query(PasswordReset).filter(PasswordReset.jti==jti).one_or_none()
    if not pr or pr.used_at is not None or pr.email.lower()!=email.lower():
        raise HTTPException(status_code=400, detail="Reset record invalid/used")

    if pr.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token expired")

    user = db.query(User).filter(User.email==email).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False                     # they’ve just set a fresh password
    user.last_password_change_at = datetime.now(timezone.utc)
    pr.used_at = datetime.now(timezone.utc)
    db.commit()

    roles = [ur.role.name for ur in user.roles]
    return TokenOut(access_token=create_access_token(user.email, roles))
```



------





# **6) Admin sets a temporary password (optional, immediate use)**





Sometimes you want admin to directly set a temp password and force change on next login (no email flow needed).

```
# app/routers/admin_users.py  (add)

class SetTempPasswordIn(BaseModel):
    email: EmailStr
    temp_password: str

@router.post("/set-temp-password")
def admin_set_temp_password(body: SetTempPasswordIn,
                            ctx=Depends(get_current_identity),
                            db: Session = Depends(get_db)):
    if not ({"admin","super_admin"} & set(ctx["roles"])):
        raise HTTPException(status_code=403, detail="Admin required")

    user = get_user_with_roles(db, body.email)
    if not user: raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(body.temp_password)
    user.must_change_password = True             # force change on next login
    db.commit()
    return {"ok": True}
```



------





# **7) UX / API contract summary**





- **Login:** POST /auth/token → { access_token, must_change_password }

  

  - If must_change_password=true, UI should immediately show **Change Password** form and call POST /auth/change-password.

  

- **First login path**

  

  - If user came via *invite* and set their password in /auth/activate, the flag is **false**.
  - If admin set a **temp password** or **reset** was requested, the flag is **true** until user changes it.

  

- **Lost password (admin-only):**

  

  - Admin hits POST /admin/users/password-reset/request → receives (and emails) reset_token.
  - User opens UI → submits POST /auth/reset/confirm with reset_token + new_password.

  

- **Server-side safety:**

  

  - Business routes include Depends(require_password_fresh()) so users flagged with must_change_password can’t call anything except password endpoints.

  





------





# **8) Test checklist (quick)**





- Login returns must_change_password=False for fresh accounts via invite.
- Admin set-temp-password → login returns must_change_password=True; business routes 403; /auth/change-password succeeds; flag clears.
- Admin password-reset/request → invalid/expired/used tokens rejected; valid token updates password and clears flag.
- Non-admin cannot call admin reset endpoints.



------

