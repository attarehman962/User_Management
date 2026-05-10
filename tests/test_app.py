import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_APP_MODULES = (
    "app.database",
    "app.auth",
    "app.models",
    "app.schemas",
    "app.dependencies",
    "app.routers.users",
    "app.routers.auth",
    "app.main",
)


def load_app(database_url: str):
    os.environ["DATABASE_URL"] = database_url
    os.environ["JWT_SECRET_KEY"] = "test-secret-key"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
    os.environ["DEFAULT_ADMIN_NAME"] = "System Admin"
    os.environ["DEFAULT_ADMIN_EMAIL"] = "admin@gmail.com"
    os.environ["DEFAULT_ADMIN_PASSWORD"] = "Admin1234"

    for name in _APP_MODULES:
        sys.modules.pop(name, None)

    database = importlib.import_module("app.database")
    auth = importlib.import_module("app.auth")
    schemas = importlib.import_module("app.schemas")
    models = importlib.import_module("app.models")
    deps = importlib.import_module("app.dependencies")
    users_router = importlib.import_module("app.routers.users")
    auth_router = importlib.import_module("app.routers.auth")
    main = importlib.import_module("app.main")

    database.create_db_and_tables()
    return database, auth, schemas, models, deps, users_router, auth_router, main


class UserManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test.db"
        (
            self.database,
            self.auth,
            self.schemas,
            self.models,
            self.deps,
            self.users,
            self.auth_router,
            self.main,
        ) = load_app(f"sqlite:///{db_path}")
        self.db = self.database.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.database.engine.dispose()
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("JWT_SECRET_KEY", None)
        os.environ.pop("ACCESS_TOKEN_EXPIRE_MINUTES", None)
        os.environ.pop("DEFAULT_ADMIN_NAME", None)
        os.environ.pop("DEFAULT_ADMIN_EMAIL", None)
        os.environ.pop("DEFAULT_ADMIN_PASSWORD", None)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def create_user(
        self,
        name: str = "Alice",
        email: str = "alice@example.com",
        password: str = "supersecure",
    ):
        return self.users.create_user(
            self.schemas.UserCreate(name=name, email=email, password=password),
            self.db,
        )

    def login_user(
        self,
        email: str = "alice@example.com",
        password: str = "supersecure",
    ):
        return self.auth_router.login_user(
            self.schemas.UserLogin(email=email, password=password),
            self.db,
        )

    def get_authenticated_user(
        self,
        email: str = "alice@example.com",
        password: str = "supersecure",
    ):
        token_response = self.login_user(email=email, password=password)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token_response.access_token,
        )
        current_user = self.deps.get_current_user(credentials, self.db)
        return token_response.access_token, current_user

    # ── Tests ──────────────────────────────────────────────────────────────────

    def test_dashboard_page_renders(self):
        response = self.main.dashboard()

        self.assertEqual(response.status_code, 200)
        body = response.body.decode()
        self.assertTrue(
            "User Management Control Center" in body
            or '<div id="root"></div>' in body
            or "React frontend build not found" in body
        )

    def test_create_user_hashes_password(self):
        created_user = self.create_user()
        stored_user = (
            self.db.query(self.models.User)
            .filter_by(id=created_user.id)
            .first()
        )

        self.assertEqual(created_user.email, "alice@example.com")
        self.assertEqual(created_user.role, "admin")
        self.assertNotEqual(stored_user.password_hash, "supersecure")
        self.assertTrue(stored_user.password_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(
            self.auth.verify_password("supersecure", stored_user.password_hash)
        )

    def test_login_returns_bearer_token_and_current_user(self):
        created_user = self.create_user()

        token_response = self.login_user()
        _, current_user = self.get_authenticated_user()

        self.assertEqual(token_response.token_type, "bearer")
        self.assertTrue(token_response.access_token)
        self.assertEqual(current_user.id, created_user.id)
        self.assertEqual(current_user.email, created_user.email)
        self.assertEqual(current_user.role, "admin")

    def test_default_admin_seed_creates_single_admin_for_empty_database(self):
        self.main.ensure_default_admin()
        self.main.ensure_default_admin()

        users = self.db.query(self.models.User).order_by(self.models.User.id.asc()).all()

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].role, "admin")
        self.assertEqual(users[0].email, "admin@gmail.com")
        self.assertTrue(
            self.auth.verify_password("Admin1234", users[0].password_hash)
        )

    def test_protected_routes_require_valid_token(self):
        with self.assertRaises(HTTPException) as exc:
            self.deps.get_current_user(None, self.db)

        self.assertEqual(exc.exception.status_code, 401)
        self.assertEqual(exc.exception.detail, "Not authenticated")

        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.value",
        )
        with self.assertRaises(HTTPException) as invalid_exc:
            self.deps.get_current_user(invalid_credentials, self.db)

        self.assertEqual(invalid_exc.exception.status_code, 401)
        self.assertEqual(invalid_exc.exception.detail, "Invalid or expired token")

    def test_full_crud_flow_with_authenticated_user(self):
        alice = self.create_user()
        bob = self.create_user(name="Bob", email="bob@example.com", password="anotherpass")
        _, current_user = self.get_authenticated_user()

        self.assertEqual(current_user.role, "admin")
        self.assertEqual(bob.role, "user")

        users = self.users.get_users(self.db, current_user)
        self.assertEqual(len(users), 2)

        fetched_user = self.users.get_single_user(bob.id, self.db, current_user)
        self.assertEqual(fetched_user.name, "Bob")

        updated_user = self.users.update_user(
            bob.id,
            self.schemas.UserUpdate(
                name="Bob Builder",
                email="builder@example.com",
                password="newbuilderpass",
            ),
            self.db,
            current_user,
        )
        self.assertEqual(updated_user.email, "builder@example.com")

        with self.assertRaises(HTTPException) as old_login_exc:
            self.login_user(email="builder@example.com", password="anotherpass")
        self.assertEqual(old_login_exc.exception.status_code, 401)

        refreshed_login = self.login_user(
            email="builder@example.com",
            password="newbuilderpass",
        )
        self.assertEqual(refreshed_login.token_type, "bearer")

        deleted = self.users.delete_user(bob.id, self.db, current_user)
        self.assertEqual(deleted, {"message": "User successfully deleted"})

        remaining = self.users.get_users(self.db, current_user)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, alice.id)

    def test_standard_user_can_view_directory_but_only_manage_self(self):
        self.create_user()
        bob = self.create_user(name="Bob", email="bob@example.com", password="anotherpass")
        _, bob_user = self.get_authenticated_user(
            email="bob@example.com",
            password="anotherpass",
        )

        visible_users = self.users.get_users(self.db, bob_user)
        self.assertEqual(len(visible_users), 2)
        self.assertEqual(visible_users[0].email, "alice@example.com")
        self.assertEqual(visible_users[1].id, bob.id)
        self.assertEqual(bob_user.role, "user")

        with self.assertRaises(HTTPException) as get_exc:
            self.users.get_single_user(1, self.db, bob_user)
        with self.assertRaises(HTTPException) as update_exc:
            self.users.update_user(
                1,
                self.schemas.UserUpdate(name="Admin Override"),
                self.db,
                bob_user,
            )
        with self.assertRaises(HTTPException) as delete_exc:
            self.users.delete_user(1, self.db, bob_user)

        self.assertEqual(get_exc.exception.status_code, 403)
        self.assertEqual(update_exc.exception.status_code, 403)
        self.assertEqual(delete_exc.exception.status_code, 403)

    def test_duplicate_email_returns_conflict(self):
        self.create_user()

        with self.assertRaises(HTTPException) as exc:
            self.create_user(name="Alice Again", email="alice@example.com", password="anotherpass")

        self.assertEqual(exc.exception.status_code, 409)
        self.assertEqual(exc.exception.detail, "Email already registered")

    def test_update_user_with_conflicting_email_returns_conflict(self):
        self.create_user()
        bob = self.create_user(name="Bob", email="bob@example.com", password="anotherpass")
        _, current_user = self.get_authenticated_user()

        with self.assertRaises(HTTPException) as exc:
            self.users.update_user(
                bob.id,
                self.schemas.UserUpdate(email="alice@example.com"),
                self.db,
                current_user,
            )

        self.assertEqual(exc.exception.status_code, 409)
        self.assertEqual(exc.exception.detail, "Email already registered")

    def test_missing_user_routes_return_not_found(self):
        self.create_user()
        _, current_user = self.get_authenticated_user()

        with self.assertRaises(HTTPException) as get_exc:
            self.users.get_single_user(999, self.db, current_user)
        with self.assertRaises(HTTPException) as update_exc:
            self.users.update_user(
                999,
                self.schemas.UserUpdate(name="Ghost User"),
                self.db,
                current_user,
            )
        with self.assertRaises(HTTPException) as delete_exc:
            self.users.delete_user(999, self.db, current_user)

        self.assertEqual(get_exc.exception.status_code, 404)
        self.assertEqual(update_exc.exception.status_code, 404)
        self.assertEqual(delete_exc.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
