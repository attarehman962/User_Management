import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODULE_NAMES = ("database", "models", "schemas", "main")


def load_app(database_url: str):
    os.environ["DATABASE_URL"] = database_url
    for module_name in MODULE_NAMES:
        sys.modules.pop(module_name, None)

    database = importlib.import_module("database")
    schemas = importlib.import_module("schemas")
    main = importlib.import_module("main")
    database.create_db_and_tables()
    return database, schemas, main


class UserManagementTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test.db"
        self.database, self.schemas, self.main = load_app(f"sqlite:///{db_path}")
        self.db = self.database.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.database.engine.dispose()
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_URL", None)

    def test_create_list_fetch_and_delete_user(self):
        created_user = self.main.create_user(
            self.schemas.UserCreate(name=" Alice ", email="alice@example.com"),
            self.db,
        )

        self.assertEqual(created_user.name, "Alice")
        self.assertEqual(created_user.email, "alice@example.com")

        users = self.main.get_users(self.db)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].id, created_user.id)

        fetched_user = self.main.get_single_user(created_user.id, self.db)
        self.assertEqual(fetched_user.email, "alice@example.com")

        deleted = self.main.delete_user(created_user.id, self.db)
        self.assertEqual(deleted, {"message": "User successfully deleted"})
        self.assertEqual(self.main.get_users(self.db), [])

    def test_duplicate_email_returns_conflict(self):
        self.main.create_user(
            self.schemas.UserCreate(name="Alice", email="alice@example.com"),
            self.db,
        )

        with self.assertRaises(self.main.HTTPException) as exc:
            self.main.create_user(
                self.schemas.UserCreate(name="Alice Again", email="alice@example.com"),
                self.db,
            )

        self.assertEqual(exc.exception.status_code, 409)
        self.assertEqual(exc.exception.detail, "Email already registered")

    def test_update_user_name_and_email(self):
        created_user = self.main.create_user(
            self.schemas.UserCreate(name="Alice", email="alice@example.com"),
            self.db,
        )

        updated_user = self.main.update_user(
            created_user.id,
            self.schemas.UserUpdate(name="Alice Cooper", email="acooper@example.com"),
            self.db,
        )

        self.assertEqual(updated_user.name, "Alice Cooper")
        self.assertEqual(updated_user.email, "acooper@example.com")

    def test_update_user_with_conflicting_email_returns_conflict(self):
        self.main.create_user(
            self.schemas.UserCreate(name="Alice", email="alice@example.com"),
            self.db,
        )
        second_user = self.main.create_user(
            self.schemas.UserCreate(name="Bob", email="bob@example.com"),
            self.db,
        )

        with self.assertRaises(self.main.HTTPException) as exc:
            self.main.update_user(
                second_user.id,
                self.schemas.UserUpdate(email="alice@example.com"),
                self.db,
            )

        self.assertEqual(exc.exception.status_code, 409)
        self.assertEqual(exc.exception.detail, "Email already registered")

    def test_update_missing_user_returns_not_found(self):
        with self.assertRaises(self.main.HTTPException) as exc:
            self.main.update_user(
                999,
                self.schemas.UserUpdate(name="Ghost User"),
                self.db,
            )

        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(exc.exception.detail, "User not found")

    def test_missing_user_returns_not_found(self):
        with self.assertRaises(self.main.HTTPException) as exc:
            self.main.get_single_user(999, self.db)

        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(exc.exception.detail, "User not found")


if __name__ == "__main__":
    unittest.main()
