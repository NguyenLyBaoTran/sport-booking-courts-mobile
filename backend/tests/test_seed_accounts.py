import ast
import re
from pathlib import Path

from backend.services.user_service.app.security import verify_password


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ROLES = {
    "admin@example.com": "ADMIN",
    "owner1@example.com": "OWNER",
    "owner2@example.com": "OWNER",
    "owner3@example.com": "OWNER",
    "owner4@example.com": "OWNER",
    "customer1@example.com": "USER",
    "customer2@example.com": "USER",
    "customer3@example.com": "USER",
    "customer4@example.com": "USER",
    "customer5@example.com": "USER",
    "customer6@example.com": "USER",
    "customer7@example.com": "USER",
    "customer8@example.com": "USER",
    "customer9@example.com": "USER",
    "customer10@example.com": "USER",
    "vy.524h0040@example.com": "USER",
    "tran.524h0130@example.com": "USER",
}


def seed_insert_accounts(path):
    source = path.read_text(encoding="utf-8")
    inserts = re.findall(
        r"INSERT INTO sports_user_db\.users.*?;", source, flags=re.DOTALL
    )
    accounts = {}
    for statement in inserts:
        match = re.search(
            r"SELECT\s+'[^']*'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,"
            r"\s*NULL\s*,\s*'([A-Z]+)'",
            statement,
            flags=re.DOTALL,
        )
        if match:
            email, password_hash, role = match.groups()
            accounts[email] = (password_hash, role)
    return accounts


def test_all_sql_seed_accounts_use_standard_emails_roles_and_password():
    base = seed_insert_accounts(ROOT / "backend/database/seed.sql")
    task4 = seed_insert_accounts(ROOT / "backend/database/seed_task4_catalogue.sql")
    accounts = {**base, **task4}

    assert set(accounts) == set(EXPECTED_ROLES)
    assert all(".demo@" not in email and email.endswith("@example.com") for email in accounts)
    assert {email: role for email, (_, role) in accounts.items()} == EXPECTED_ROLES
    hashes = {password_hash for password_hash, _ in accounts.values()}
    assert len(hashes) == 1
    assert verify_password("password123", next(iter(hashes)))


def test_legacy_aliases_are_renamed_in_place_and_conflicts_stop_the_seed():
    base = (ROOT / "backend/database/seed.sql").read_text(encoding="utf-8")
    task4 = (ROOT / "backend/database/seed_task4_catalogue.sql").read_text(encoding="utf-8")
    mappings = {}
    for source in (base, task4):
        mappings.update(
            re.findall(
                r"WHEN '([^']+\.demo@example\.com)' THEN '([^']+@example\.com)'",
                source,
            )
        )

    expected = {email.replace("@example.com", ".demo@example.com"): email for email in EXPECTED_ROLES}
    assert mappings == expected
    assert "legacy.id <> standardized.id" in base
    assert "legacy.id <> standardized.id" in task4


def test_seed_preserves_already_standard_password_hashes():
    standard_hash = "$argon2id$v=19$m=65536,t=3,p=4$2EwLRj8tbULNdDfRwR7E2w$YCmmQNpMQPkxFEjaOKkn9s/22CVbdDRMts4HEIPzItk"
    for name in ("seed.sql", "seed_task4_catalogue.sql"):
        source = (ROOT / "backend/database" / name).read_text(encoding="utf-8")
        assert f"WHEN password_hash = '{standard_hash}' THEN password_hash" in source


def test_api_booking_seed_uses_only_standard_customers_and_shared_password():
    path = ROOT / "backend/scripts/seed_demo_bookings.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignments = {
        target.id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id in {"CUSTOMERS"}
    }
    customers = assignments["CUSTOMERS"]
    assert len(customers) == 12
    assert all(".demo@" not in email and email.endswith("@example.com") for email in customers)
    assert {"vy.524h0040@example.com", "tran.524h0130@example.com"} <= set(customers)
    assert 'password = "password123"' in path.read_text(encoding="utf-8")


def test_readme_lists_all_seed_logins_with_the_common_password():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| (?:Admin|Owner|Customer) \| `([^`]+)` \| `([^`]+)` \|$",
        readme,
        flags=re.MULTILINE,
    )
    assert len(rows) == len(EXPECTED_ROLES)
    assert {email for email, _ in rows} == set(EXPECTED_ROLES)
    assert all(password == "password123" for _, password in rows)
