# AUTH.md
> Authentication flow and user-data isolation — as of 2026-11-01

---

## Implementation

Custom bcrypt + PyJWT. No third-party auth provider (Auth0, Clerk, Firebase, etc.).

**Why custom:** Interviewers ask "walk me through your auth." Using a third-party provider makes that question impossible to answer with depth.

---

## Files

| File | Responsibility |
|---|---|
| `backend/app/services/auth.py` | `hash_password`, `verify_password`, `create_access_token`, `get_current_user` |
| `backend/app/routers/auth.py` | `POST /register`, `POST /login`, `GET /me` |
| `backend/app/models/user.py` | `User` table: id, email, hashed_password, created_at |
| `backend/app/config.py` | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| `frontend/js/app.js` | Token stored in `localStorage` under key `rb_token` |

---

## Registration flow

```
POST /api/v1/auth/register  { email, password }
  │
  ├── Pydantic validates: email format, password min length
  ├── Check: db.query(User).filter(User.email == email).first() → 409 if exists
  ├── hash_password(plain) → bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
  ├── db.add(User(id=uuid4(), email=email.lower(), hashed_password=...))
  └── return UserResponse (id, email, created_at) — never the hash
```

---

## Login flow

```
POST /api/v1/auth/login  { email, password }
  │
  ├── db.query(User).filter(User.email == email.lower()).first()
  ├── verify_password(plain, hashed) → bcrypt.checkpw(...) → 401 if mismatch
  ├── create_access_token(user_id)
  │     payload = {"sub": user_id, "exp": now + 7 days}
  │     jwt.encode(payload, SECRET_KEY, algorithm="HS256")
  └── return { access_token: "eyJ..." }
```

---

## Token validation (every protected request)

```
Authorization: Bearer <token>
  │
  └── FastAPI dependency: get_current_user(credentials, db)
        │
        ├── _decode_token(credentials.credentials)
        │     jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        │     ExpiredSignatureError → 401 "Token has expired"
        │     PyJWTError → 401 "Invalid or expired token"
        │     Returns: user_id = payload["sub"]
        │
        ├── db.query(User).filter(User.id == user_id).first()
        │     Not found → 401 "User not found"
        │
        └── Returns: User ORM object → injected as `current_user` into route handlers
```

Every protected route has `current_user: User = Depends(get_current_user)`.

---

## User-data isolation

**Rule:** Never trust a client-supplied user_id. Always derive it from the token.

Every service function that touches user data takes `user_id: str` as a parameter — injected from `current_user.id` in the router. This means:

```python
# Router injects verified user_id
def get_entry(entry_id: str, db: Session, current_user: User = Depends(get_current_user)):
    return journal_service.get_entry(db, entry_id, user_id=current_user.id)

# Service enforces ownership via WHERE clause
def get_entry(db, entry_id, user_id):
    return db.query(JournalEntry).filter(
        JournalEntry.id == entry_id,
        JournalEntry.user_id == user_id   # <-- isolation enforced here
    ).first()
```

This pattern is applied in:
- `services/journal.py` — all entry queries
- `services/goals.py` — all goal queries
- `services/checkin.py` — all habit log queries
- `services/onboarding.py` — all onboarding data queries
- `services/journal.py:semantic_search()` — SQL `WHERE user_id = :user_id`

**Semantic search isolation** is enforced at the SQL level: `WHERE user_id = :user_id AND embedding IS NOT NULL`. A vector search can never return another user's entries.

---

## Token storage and expiry

- **Storage:** `localStorage.rb_token` — persists across browser sessions
- **Expiry:** 7 days (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` in `config.py`)
- **Frontend handling:** Every 401 response calls `handleUnauthorized()` → clears `rb_token` → redirects to auth view

---

## What to preserve

Do not replace this auth system. It works correctly, is well-understood, and provides good interview material. New features (calendar events, tasks, chat) should follow the exact same pattern: derive user_id from `current_user.id` in the router, pass it down to the service layer, and filter all DB queries by it.

---

## Security notes

- Passwords are never logged or returned in API responses.
- `User.email` is stored and compared lowercased.
- `SECRET_KEY` defaults to `"dev-secret-change-me-in-production"` — must be overridden in `.env` or Vercel environment variables.
- CORS is currently `allow_origins=["*"]` — acceptable for a personal app, tighten for anything shared.
- No refresh token implementation — users log in again after 7 days.
