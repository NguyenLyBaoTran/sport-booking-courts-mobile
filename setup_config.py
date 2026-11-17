"""Interactive, cross-platform local setup for Sports Court Booking."""

from __future__ import annotations

import getpass
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, ContextManager, Mapping, Sequence
from http.client import HTTPResponse
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
VENV_DIR = BACKEND_DIR / ".venv"
DEV_REQUIREMENTS = BACKEND_DIR / "requirements-dev.txt"
RUNTIME_REQUIREMENTS = BACKEND_DIR / "requirements.txt"
VENV_REQUIREMENTS_MARKER = VENV_DIR / ".requirements-dev.sha256"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
DEV_MYSQL_VOLUME = "sport-court-booking-mysql-dev"
COMPOSE_COMMAND_TIMEOUT = 900
COMPOSE_HEALTH_TIMEOUT = 720
HEALTH_POLL_INTERVAL = 5
HEALTH_PROGRESS_INTERVAL = 30
LOCAL_SECRET_MINIMUMS = {
    "MYSQL_DEV_ROOT_PASSWORD": 20,
    "JWT_SECRET_KEY": 32,
    "INTERNAL_SERVICE_TOKEN": 32,
}
ANDROID_LOCAL_PROPERTIES = ROOT / "android-user" / "google-oauth.local.properties"
PLACEHOLDERS = ("replace_with_", "your_", "<", ">", "changeme")
GOOGLE_CLIENT_ID_RE = re.compile(r"^[0-9]+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$")
SHA1_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}:?){20}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
HEALTHY_SERVICES = {
    "mysql-dev", "mailpit-dev", "user-service", "court-service", "booking-service",
    "payment-service", "gateway", "management-web",
}
FIXED_PORT_LABELS = {"gateway": "API Gateway", "management-web": "Management Web", "mailpit-dev": "Mailpit SMTP / UI"}
ANDROID_PACKAGE_NAME = "com.example.sportbooking"
MANAGED_ENV_KEYS = {
    "MYSQL_DEV_ROOT_PASSWORD", "JWT_SECRET_KEY", "INTERNAL_SERVICE_TOKEN",
    "SMTP_PROVIDER", "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_STARTTLS",
    "GOOGLE_LOGIN_ENABLED", "GOOGLE_CLIENT_ID", "GOOGLE_ANDROID_CLIENT_ID", "GOOGLE_ANDROID_PACKAGE_NAME", "GOOGLE_ANDROID_SHA1",
    "DATABASE_URL", "USER_DATABASE_URL", "COURT_DATABASE_URL", "BOOKING_DATABASE_URL", "PAYMENT_DATABASE_URL",
}


class SetupError(RuntimeError):
    pass


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _requirements_fingerprint() -> str:
    import hashlib

    digest = hashlib.sha256()
    for path in (RUNTIME_REQUIREMENTS, DEV_REQUIREMENTS):
        if not path.is_file():
            raise SetupError(f"Required Python dependency manifest is missing: {path.relative_to(ROOT)}")
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _check_python_environment(run: Callable[..., subprocess.CompletedProcess[str]]) -> bool:
    python = _venv_python()
    if not python.is_file():
        return False
    try:
        pip_check = run([str(python), "-m", "pip", "check"], cwd=ROOT, capture_output=True, text=True, check=False)
        imports = run([
            str(python), "-c",
            "import alembic, argon2, cryptography, email_validator, fastapi, httpx, jose, pymysql, pydantic, pydantic_settings, pwdlib, pytest, requests, sqlalchemy, uvicorn, google.auth, dotenv",
        ], cwd=ROOT, capture_output=True, text=True, check=False)
    except OSError:
        return False
    return pip_check.returncode == 0 and imports.returncode == 0


def _ensure_python_environment(
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    *,
    confirm_repair: Callable[[str, bool], bool] | None = None,
) -> None:
    """Create/reuse backend/.venv and install the shared backend dev requirements."""
    fingerprint = _requirements_fingerprint()
    existed = VENV_DIR.exists()
    current_fingerprint = VENV_REQUIREMENTS_MARKER.read_text(encoding="ascii").strip() if VENV_REQUIREMENTS_MARKER.is_file() else ""
    healthy = _check_python_environment(run) if existed else False
    if existed and healthy and current_fingerprint == fingerprint:
        print("Python development environment is ready; dependencies are unchanged.")
        return
    if confirm_repair is None:
        confirm_repair = _yes_no
    if existed and not confirm_repair("Update or repair the existing backend/.venv dependencies?", True):
        raise SetupError("The existing backend/.venv is missing or out of date. Rerun setup and approve dependency repair.")

    if not existed:
        print("Creating backend/.venv...")
        try:
            result = run([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=ROOT, capture_output=True, text=True, check=False)
        except OSError:
            raise SetupError("Could not create backend/.venv. Verify that the selected Python installation includes the venv module.") from None
        if result.returncode != 0:
            raise SetupError("Could not create backend/.venv. Verify that Python's venv support is installed; the existing files were left untouched.")
        if not _venv_python().is_file():
            raise SetupError("Python reported success but backend/.venv has no interpreter. Inspect the environment before retrying.")

    print("Installing backend development dependencies into backend/.venv...")
    try:
        install = run([
            str(_venv_python()), "-m", "pip", "install", "-r", str(DEV_REQUIREMENTS),
        ], cwd=ROOT, capture_output=True, text=True, check=False)
    except OSError:
        raise SetupError("Could not run pip in backend/.venv. The environment was preserved; inspect Python and retry setup.") from None
    if install.returncode != 0:
        raise SetupError("Backend dependency installation failed. backend/.venv was preserved; check network/package-index access and rerun setup to repair it.")
    if not _check_python_environment(run):
        raise SetupError("Backend dependencies were installed but validation failed. backend/.venv was preserved; rerun setup to repair it.")
    VENV_REQUIREMENTS_MARKER.write_text(fingerprint + "\n", encoding="ascii")
    print("Python development environment is ready.")


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1].replace("\\'", "'")
        elif value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        values[key] = value
    return values


def _check_duplicate_managed_keys(path: Path) -> None:
    if not path.exists():
        return
    found: set[str] = set()
    duplicates: set[str] = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in MANAGED_ENV_KEYS:
            if key in found:
                duplicates.add(key)
            found.add(key)
    if duplicates:
        raise SetupError("Duplicate setup-managed .env keys: " + ", ".join(sorted(duplicates)) + ". Remove duplicate key lines manually; values were not changed.")


def _write_env(path: Path, updates: Mapping[str, str]) -> None:
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
        if key in remaining:
            output.append(f"{key}={remaining.pop(key)}")
        else:
            output.append(line)
    if output and output[-1].strip():
        output.append("")
    output.extend(f"{key}={value}" for key, value in remaining.items())
    path.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")


def _write_android_google_id(web_client_id: str, enabled: bool = False) -> None:
    path = ANDROID_LOCAL_PROPERTIES
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    values["GOOGLE_SERVER_CLIENT_ID"] = web_client_id
    values["GOOGLE_LOGIN_ENABLED"] = str(enabled).lower()
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")


def _effective_service_binding(
    run: Callable[..., subprocess.CompletedProcess[str]],
    values: Mapping[str, str],
    service: str,
    target_port: int,
) -> tuple[str, int]:
    result = _compose(run, ["--profile", "dev", "config", "--format", "json"], values)
    if result.returncode != 0:
        raise SetupError(f"Could not determine the configured {service} host port.")
    try:
        services = json.loads(result.stdout)["services"]
        bindings = services[service]["ports"]
        matching = [binding for binding in bindings if int(binding["target"]) == target_port]
        published = {(str(item.get("host_ip", "")), int(item["published"])) for item in matching}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise SetupError(f"Compose returned invalid published port configuration for {service}.") from None
    if len(published) != 1:
        raise SetupError(f"Compose must publish exactly one valid host port for {service} target {target_port}.")
    host, port = next(iter(published))
    if port < 1 or port > 65535:
        raise SetupError(f"Compose returned an invalid published port for {service}.")
    return host, port


def _local_url_host(bind_address: str) -> str:
    return "127.0.0.1" if bind_address in {"", "0.0.0.0", "::"} else bind_address


def _format_url_host(host: str) -> str:
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def _verify_gateway_health(
    run: Callable[..., subprocess.CompletedProcess[str]],
    values: Mapping[str, str],
    *,
    request: Callable[..., ContextManager[HTTPResponse]] = urlopen,
) -> dict[str, bool]:
    bind_address, port = _effective_service_binding(run, values, "gateway", 8000)
    base_url = f"http://{_format_url_host(_local_url_host(bind_address))}:{port}"
    paths = (
        "/health",
        "/api/v1/user/health",
        "/api/v1/court/health",
        "/api/v1/booking/health",
        "/api/v1/payment/health",
    )
    results: dict[str, bool] = {}
    for path in paths:
        try:
            with request(base_url + path, timeout=5) as response:
                results[path] = 200 <= int(getattr(response, "status", 200)) < 300
        except Exception:
            results[path] = False
    return results


def _yes_no(prompt: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{prompt} {suffix}: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer y or n.")


def _choice(prompt: str, choices: Sequence[str], default: str) -> str:
    labels = {
        "mailpit": ("Mailpit (Recommended)", "Keeps emails local on your computer. No real email is sent; useful for development and testing."),
        "gmail": ("Gmail SMTP", "Sends real emails through your Gmail account. Requires a Gmail address and App Password."),
        "disabled": ("Disabled (Recommended)", "Users sign in with email and password. No Google OAuth configuration is required."),
        "enabled": ("Enabled", "Allows Google sign-in. Requires valid Google OAuth configuration."),
        "retry": ("Try again", "Enter the Google OAuth values again."),
    }
    while True:
        print(f"\n{prompt}:")
        for index, choice in enumerate(choices, start=1):
            title, description = labels.get(choice, (choice, ""))
            marker = " (default)" if choice == default else ""
            print(f"[{index}] {title}{marker}")
            if description:
                print(f"    {description}")
        answer = input(f"Choose [1-{len(choices)}] (default: {choices.index(default) + 1}): ").strip()
        if not answer:
            return default
        if answer.isdecimal() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        print(f"Invalid choice. Enter a number from 1 to {len(choices)}; press Enter for the default.")


def _needs_generated_secret(value: str) -> bool:
    return not value or any(marker in value.lower() for marker in PLACEHOLDERS)


def _generate_local_secret(minimum: int) -> str:
    """Generate a URL-safe secret accepted by Compose and backend validation."""
    return secrets.token_urlsafe(max(32, minimum))


def _ensure_dev_mysql_volume_absent(
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Refuse to invent required secrets when an existing Dev volume may hold data."""
    try:
        result = run(
            ["docker", "volume", "ls", "--filter", f"name={DEV_MYSQL_VOLUME}", "--format", "{{.Name}}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except OSError:
        raise SetupError("Could not check for an existing Dev MySQL volume; no secrets were generated and .env was not changed.") from None
    if result.returncode != 0:
        raise SetupError("Could not check for an existing Dev MySQL volume; no secrets were generated and .env was not changed.")
    if DEV_MYSQL_VOLUME in (result.stdout or "").splitlines():
        raise SetupError(
            "The Dev MySQL volume already exists and a required local secret is missing or still a template. "
            "Setup did not change .env. Restore the original secret values used by this volume before retrying."
        )


def _configuration_updates(existing: Mapping[str, str] | None = None) -> dict[str, str]:
    existing = existing or {}
    updates: dict[str, str] = {}
    for key, minimum in LOCAL_SECRET_MINIMUMS.items():
        value = existing.get(key, "")
        if _needs_generated_secret(value):
            value = _generate_local_secret(minimum)
        updates[key] = value

    print("\nEmail configuration")
    provider = _choice("Choose how the application sends email", ("mailpit", "gmail"), "mailpit")
    if provider == "mailpit":
        updates.update({
            "SMTP_PROVIDER": "mailpit",
            "SMTP_HOST": "mailpit-dev",
            "SMTP_PORT": "1025",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
            "SMTP_FROM": "noreply@sport-booking.test",
            "SMTP_STARTTLS": "false",
        })
    else:
        email = input("Sender Gmail address: ").strip()
        password = getpass.getpass("Gmail App Password (not your normal password; input hidden): ").strip().replace(" ", "")
        if not EMAIL_RE.fullmatch(email):
            raise SetupError("Enter a valid sender email address.")
        if not re.fullmatch(r"[A-Za-z0-9]{16}", password):
            raise SetupError("Gmail App Password must contain the 16 letters/numbers shown by Google; spaces are ignored.")
        updates.update({
            "SMTP_PROVIDER": "gmail",
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": email,
            "SMTP_PASSWORD": password,
            "SMTP_FROM": email,
            "SMTP_STARTTLS": "true",
        })

    return _configure_google_login(updates)


def _configure_google_login(values: dict[str, str]) -> dict[str, str]:
    def disable_google() -> dict[str, str]:
        values.update({
            "GOOGLE_LOGIN_ENABLED": "false",
            "GOOGLE_CLIENT_ID": "",
            "GOOGLE_ANDROID_CLIENT_ID": "",
            "GOOGLE_ANDROID_PACKAGE_NAME": ANDROID_PACKAGE_NAME,
            "GOOGLE_ANDROID_SHA1": "",
        })
        return values

    while True:
        print("\nGoogle Login configuration")
        google = _choice("Choose whether to enable Google Login", ("disabled", "enabled"), "disabled")
        if google == "disabled":
            return disable_google()

        print("Use OAuth client IDs from your Google Cloud project. Never provide a Google Client Secret.")
        web_id = input("Google Web Client ID (backend audience and Android ID-token request): ").strip()
        android_id = input("Google Android Client ID: ").strip()
        print(f"Android package is fixed at {ANDROID_PACKAGE_NAME}; use this exact package when creating the Android OAuth client in Google Cloud.")
        package = input(f"Confirm Android package name [{ANDROID_PACKAGE_NAME}]: ").strip() or ANDROID_PACKAGE_NAME
        sha1 = input("Android signing SHA-1 (colon-separated; see docs if unknown): ").strip().upper()
        problem = ""
        if not GOOGLE_CLIENT_ID_RE.fullmatch(web_id):
            problem = "Google Web Client ID is missing or invalid."
        elif not GOOGLE_CLIENT_ID_RE.fullmatch(android_id):
            problem = "Google Android Client ID is missing or invalid."
        elif package != ANDROID_PACKAGE_NAME:
            problem = f"This app uses {ANDROID_PACKAGE_NAME}; a different package cannot be configured by setup."
        elif not SHA1_RE.fullmatch(sha1):
            problem = "Signing SHA-1 is missing or invalid. Run the Gradle signingReport task to find it."
        if problem:
            print(problem)
            retry = _choice(
                "Google Login is not enabled until all values are valid",
                ("disabled", "retry"),
                "disabled",
            )
            if retry == "disabled":
                return disable_google()
            continue
        values.update({
            "GOOGLE_LOGIN_ENABLED": "true",
            "GOOGLE_CLIENT_ID": web_id,
            "GOOGLE_ANDROID_CLIENT_ID": android_id,
            "GOOGLE_ANDROID_PACKAGE_NAME": package,
            "GOOGLE_ANDROID_SHA1": sha1,
        })
        _write_android_google_id(web_id, enabled=True)
        return values


def _validate_configuration(values: Mapping[str, str]) -> None:
    for key, minimum in (("MYSQL_DEV_ROOT_PASSWORD", 20), ("JWT_SECRET_KEY", 32), ("INTERNAL_SERVICE_TOKEN", 32)):
        value = values.get(key, "")
        if len(value) < minimum or any(marker in value.lower() for marker in PLACEHOLDERS):
            raise SetupError(f"{key} is missing or still a template. Edit the existing root .env manually; setup will not change it.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise SetupError(f"{key} must use URL-safe letters, numbers, '_' or '-'.")
    if values.get("SMTP_PROVIDER") == "gmail":
        if not EMAIL_RE.fullmatch(values.get("SMTP_USERNAME", "")) or not EMAIL_RE.fullmatch(values.get("SMTP_FROM", "")) or not re.fullmatch(r"[A-Za-z0-9]{16}", values.get("SMTP_PASSWORD", "")):
            raise SetupError("Gmail SMTP configuration is incomplete. Update the local .env or rerun setup.")
        if values.get("SMTP_HOST") != "smtp.gmail.com" or values.get("SMTP_PORT") != "587" or values.get("SMTP_STARTTLS", "").lower() != "true":
            raise SetupError("Gmail SMTP must use smtp.gmail.com:587 with STARTTLS enabled.")
    elif values.get("SMTP_PROVIDER", "mailpit") == "mailpit":
        if values.get("SMTP_HOST", "mailpit-dev") != "mailpit-dev" or values.get("SMTP_PORT", "1025") != "1025" or values.get("SMTP_STARTTLS", "false").lower() != "false" or values.get("SMTP_USERNAME", "") or values.get("SMTP_PASSWORD", ""):
            raise SetupError("Mailpit SMTP must use mailpit-dev:1025 with STARTTLS disabled.")
    else:
        raise SetupError("SMTP_PROVIDER must be mailpit or gmail.")

    google_flag = values.get("GOOGLE_LOGIN_ENABLED", "false").strip().lower()
    if google_flag not in {"true", "false"}:
        raise SetupError("GOOGLE_LOGIN_ENABLED must be true or false.")
    enabled = google_flag == "true"
    web_id = values.get("GOOGLE_CLIENT_ID", "")
    android_id = values.get("GOOGLE_ANDROID_CLIENT_ID", "")
    if enabled:
        package = values.get("GOOGLE_ANDROID_PACKAGE_NAME", "")
        sha1 = values.get("GOOGLE_ANDROID_SHA1", "")
        if not GOOGLE_CLIENT_ID_RE.fullmatch(web_id) or not GOOGLE_CLIENT_ID_RE.fullmatch(android_id):
            raise SetupError("Google Login is enabled but valid Web and Android Client IDs are required.")
        if package != ANDROID_PACKAGE_NAME or not SHA1_RE.fullmatch(sha1):
            raise SetupError("Google Login also requires a valid Android package name and signing SHA-1.")


def _check_docker(run: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    for command, label in ((["docker", "info"], "Docker Engine"), (["docker", "compose", "version"], "Docker Compose v2")):
        try:
            result = run(command, cwd=ROOT, capture_output=True, text=True, check=False, timeout=30)
        except OSError:
            raise SetupError(f"{label} is unavailable. Install/start Docker Desktop or Docker Engine with Compose v2.") from None
        if result.returncode != 0:
            raise SetupError(f"{label} is not ready. Start Docker and retry; command output was suppressed.")


def _json_records(output: str) -> list[dict]:
    output = output.strip()
    if not output:
        return []
    try:
        parsed = json.loads(output)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        return [parsed] if isinstance(parsed, dict) else []
    except json.JSONDecodeError:
        records = []
        for line in output.splitlines():
            try:
                record = json.loads(line)
                if isinstance(record, dict):
                    records.append(record)
            except json.JSONDecodeError:
                continue
        return records


def _compose_published_ports(output: str) -> set[tuple[str, int]]:
    ports: set[tuple[str, int]] = set()
    for record in _json_records(output):
        publishers = record.get("Publishers", [])
        if isinstance(publishers, list):
            for item in publishers:
                if isinstance(item, dict):
                    try:
                        ports.add((str(item.get("URL", "")), int(item.get("PublishedPort", item.get("Published", 0)))))
                    except (TypeError, ValueError):
                        pass
    return ports


def _check_ports(run: Callable[..., subprocess.CompletedProcess[str]], values: Mapping[str, str]) -> None:
    config = _compose(run, ["--profile", "dev", "config", "--format", "json"], values)
    if config.returncode != 0:
        raise SetupError("Could not read effective Compose port configuration; check the root .env and Compose file.")
    try:
        services = json.loads(config.stdout)["services"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise SetupError("Compose returned an invalid port configuration; no ports were checked.") from None
    configured: dict[int, tuple[str, str]] = {}
    for service, spec in services.items():
        service_name = service if isinstance(service, str) else str(service)
        label = FIXED_PORT_LABELS.get(service_name, service_name)
        for binding in spec.get("ports", []):
            try:
                configured[int(binding["published"])] = (label, str(binding.get("host_ip", "")))
            except (KeyError, TypeError, ValueError):
                continue

    ps = _compose(run, ["--profile", "dev", "ps", "--format", "json"], values)
    if ps.returncode != 0:
        raise SetupError("Could not identify ports already published by this Compose project.")
    owned_ports = _compose_published_ports(ps.stdout)
    busy: list[str] = []
    for port, (label, configured_host) in configured.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((configured_host or "0.0.0.0", port))
        except OSError:
            own_binding = any(published == port and (not configured_host or configured_host in {"0.0.0.0", "::"} or host == configured_host) for host, published in owned_ports)
            if not own_binding:
                busy.append(f"{label} ({port})")
        finally:
            sock.close()
    if busy:
        raise SetupError("These configured ports are already in use by an unrelated process or project: " + ", ".join(busy) + ". Stop that service or change the corresponding host port in the root .env.")


def _compose_environment(values: Mapping[str, str]) -> dict[str, str]:
    environment = os.environ.copy()
    # Ensure shell variables cannot silently override the local .env choices.
    for key in set(values) | set(_parse_env(ENV_FILE)):
        environment.pop(key, None)
    # Keep startup scoped to the selected Dev profile, regardless of shell state.
    environment.pop("COMPOSE_PROFILES", None)
    return environment


def _compose(run: Callable[..., subprocess.CompletedProcess[str]], args: Sequence[str], values: Mapping[str, str]) -> subprocess.CompletedProcess[str]:
    command = [
        "docker", "compose", "--env-file", str(ENV_FILE),
        "--project-name", "sports-court-booking", "--file", str(ROOT / "compose.yaml"),
        *args,
    ]
    # Bound image pulls/builds separately from the health polling window.
    timeout = COMPOSE_COMMAND_TIMEOUT if "up" in args or "build" in args else 60
    try:
        result = run(command, cwd=ROOT, env=_compose_environment(values), capture_output=True, text=True, check=False, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        excerpt = _redact_logs(str(output) + ("\n" + str(stderr) if stderr else ""), values)
        if excerpt:
            print("\nDocker Compose output before timeout (secrets redacted):\n" + excerpt[-5000:], file=sys.stderr)
        action = "pull/build/start" if "up" in args or "build" in args else "command"
        raise SetupError(f"Docker Compose {action} timed out after {timeout} seconds. Existing data was left intact; inspect service state and logs before retrying.") from None
    except OSError:
        raise SetupError("Could not run Docker Compose. Verify Docker is installed and running.") from None
    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    show_output = result.returncode != 0 or "up" in args or "build" in args
    if output.strip() and show_output:
        stream = sys.stderr if result.returncode != 0 else sys.stdout
        print("\nDocker Compose output (secrets redacted):\n" + _redact_logs(output, values)[-5000:], file=stream)
    return result


def _redact_logs(output: str, values: Mapping[str, str]) -> str:
    redacted = output
    for key in ("MYSQL_DEV_ROOT_PASSWORD", "JWT_SECRET_KEY", "INTERNAL_SERVICE_TOKEN", "SMTP_PASSWORD"):
        secret = values.get(key, "")
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    redacted = re.sub(r"(?i)(mysql(?:\+pymysql)?://)[^\s/@]+:[^\s/@]*@", r"\1[REDACTED]@", redacted)
    redacted = re.sub(r"(?im)((?:password|token|secret)(?:=|:\s*)\s*)[^\r\n]*", r"\1[REDACTED]", redacted)
    return redacted.strip()


def _failed_service_error(run: Callable[..., subprocess.CompletedProcess[str]], name: str, state: str, values: Mapping[str, str]) -> SetupError:
    logs = _compose(run, ["--profile", "dev", "logs", "--tail", "40", name], values)
    excerpt = _redact_logs(logs.stdout + ("\n" + logs.stderr if logs.stderr else ""), values)
    suffix = f"\nRecent {name} logs (secrets redacted):\n{excerpt}" if excerpt else ""
    if name == "schema-init":
        prefix = "Development schema initialization failed."
    elif name == "seed":
        prefix = f"Development demo seed failed ({state})."
    else:
        prefix = f"Service `{name}` entered state `{state}` during startup."
    return SetupError(f"{prefix} Setup stopped; no recovery restart or resource cleanup was attempted.{suffix}")


def _recent_service_logs(
    run: Callable[..., subprocess.CompletedProcess[str]],
    services: Sequence[str],
    values: Mapping[str, str],
) -> str:
    try:
        result = _compose(run, ["--profile", "dev", "logs", "--tail", "40", *services], values)
    except SetupError:
        return ""
    excerpt = _redact_logs(result.stdout + ("\n" + result.stderr if result.stderr else ""), values)
    return f"\nRecent {', '.join(services)} logs (secrets redacted):\n{excerpt[-5000:]}" if excerpt else ""


def _wait_healthy(
    run: Callable[..., subprocess.CompletedProcess[str]],
    values: Mapping[str, str],
    timeout: int = COMPOSE_HEALTH_TIMEOUT,
    *,
    required_services: set[str] | None = None,
    require_schema_init: bool = True,
    required_completed_services: set[str] | None = None,
) -> dict[str, str]:
    deadline = time.monotonic() + timeout
    if required_services is None:
        required_services = set(HEALTHY_SERVICES)
    completed_services = set(required_completed_services or ())
    if require_schema_init:
        completed_services.add("schema-init")
    pending = set(required_services) | completed_services
    last_progress = time.monotonic()
    observed: dict[str, dict[str, str]] = {}
    while time.monotonic() < deadline:
        # One-shot initializers succeed by exiting, so they must be included.
        result = _compose(run, ["--profile", "dev", "ps", "--all", "--format", "json"], values)
        if result.returncode != 0:
            raise SetupError("Could not read Compose service state (ps --all failed). Run docker compose --profile dev ps --all for details.")
        states: dict[str, str] = {}
        records = _json_records(result.stdout)
        if result.stdout.strip() and not records:
            raise SetupError("Could not parse Docker Compose service state JSON from ps --all; inspect docker compose --profile dev ps --all.")
        for record in records:
            name = _compose_record_service(record)
            if not name:
                continue
            state = str(record.get("State", "")).strip().lower()
            health = str(record.get("Health", "")).strip().lower()
            observed[name] = {"state": state or "unknown", "health": health or "none"}
            if name in completed_services:
                if state == "exited":
                    try:
                        exit_code = int(record["ExitCode"])
                    except (KeyError, TypeError, ValueError):
                        raise SetupError(f"{name} is exited but Compose did not report a valid ExitCode; inspect docker compose --profile dev ps --all.") from None
                    if exit_code == 0:
                        states[name] = "completed"
                    else:
                        raise _failed_service_error(run, name, f"exited with code {exit_code}", values)
                elif state in {"running", "restarting", "created", "paused"}:
                    states[name] = state
                elif state in {"dead", "removing"}:
                    raise _failed_service_error(run, name, state, values)
                else:
                    states[name] = state or "unknown"
                continue
            states[name] = health if health else state
            if name in required_services and state in {"restarting", "restart", "dead", "exited"}:
                raise _failed_service_error(run, name, state, values)
            if name in required_services and health == "unhealthy":
                raise _failed_service_error(run, name, "unhealthy", values)
        missing_completed = sorted(name for name in completed_services if name not in states)
        if missing_completed:
            raise SetupError(f"Compose returned no container record for required one-shot service(s): {', '.join(missing_completed)}. Check docker compose --profile dev ps --all and service dependencies.")
        pending = {name for name in required_services if states.get(name) != "healthy"}
        pending.update(name for name in completed_services if states.get(name) != "completed")
        if not pending:
            return states
        now = time.monotonic()
        if now - last_progress >= HEALTH_PROGRESS_INTERVAL:
            progress = ", ".join(
                f"{name}={observed.get(name, {}).get('state', 'not found')}"
                + (f"/{observed[name]['health']}" if name in observed and observed[name]["health"] != "none" else "")
                for name in sorted(pending)
            )
            print(f"Still waiting for services: {progress} ({max(0, int(deadline - now))}s remaining).")
            last_progress = now
        time.sleep(min(HEALTH_POLL_INTERVAL, max(0, deadline - now)))
    details = ", ".join(sorted(pending))
    missing = sorted(name for name in pending if name not in observed)
    if missing:
        raise SetupError(f"Timed out after {timeout}s waiting for services: {details}. No container record was returned for: {', '.join(missing)}. Check docker compose --profile dev ps --all.")
    # At timeout, collect diagnostics for every pending service; choosing one by
    # sort order would often point at an unrelated dependency.
    diagnostic = _recent_service_logs(run, sorted(pending), values)
    observed_text = ", ".join(f"{name}={observed[name]['state']}/{observed[name]['health']}" for name in sorted(pending))
    raise SetupError(f"Timed out after {timeout}s waiting for services: {details}. Last observed: {observed_text}.{diagnostic}")


def _compose_record_service(record: Mapping[str, object]) -> str:
    """Resolve service identity across Compose ps JSON formats."""
    service = record.get("Service")
    if isinstance(service, str) and service.strip():
        return service.strip()
    labels = record.get("Labels")
    if isinstance(labels, str):
        for label in labels.split(","):
            key, separator, value = label.partition("=")
            if separator and key.strip() == "com.docker.compose.service" and value.strip():
                return value.strip()
    elif isinstance(labels, Mapping):
        service = labels.get("com.docker.compose.service")
        if isinstance(service, str) and service.strip():
            return service.strip()
    # Last resort for older output that omits both service and labels.
    names = record.get("Names") or record.get("Name")
    if isinstance(names, str):
        names = names.split(",", 1)[0].strip()
    if isinstance(names, str) and names.strip():
        container_name = names.strip()
        for candidate in sorted(HEALTHY_SERVICES | {"schema-init", "seed"}, key=len, reverse=True):
            if re.search(rf"-{re.escape(candidate)}-\d+$", container_name):
                return candidate
    return ""


def _start_dev_services(
    run: Callable[..., subprocess.CompletedProcess[str]],
    values: Mapping[str, str],
) -> dict[str, str]:
    stages = (
        (
            "6/11 Starting Dev MySQL and Mailpit...",
            ["--profile", "dev", "up", "-d", "mysql-dev", "mailpit-dev"],
            {"mysql-dev", "mailpit-dev"}, False,
        ),
        (
            "7/11 Creating the four Dev database schemas...",
            ["--profile", "dev", "up", "-d", "schema-init"],
            set(), True,
        ),
        (
            "8/11 Starting backend services (User migrations and service table initialization run here)...",
            ["--profile", "dev", "up", "-d", "user-service", "court-service", "booking-service", "payment-service"],
            {"user-service", "court-service", "booking-service", "payment-service"}, False,
        ),
        (
            "9/11 Seeding and verifying the local demo catalogue...",
            ["--profile", "dev", "up", "-d", "seed"],
            set(), False,
        ),
        (
            "10/11 Starting the API Gateway...",
            ["--profile", "dev", "up", "-d", "gateway"],
            {"gateway"}, False,
        ),
        (
            "11/11 Starting Management Web...",
            ["--profile", "dev", "up", "-d", "management-web"],
            {"management-web"}, False,
        ),
    )
    states: dict[str, str] = {}
    for message, args, services, schema_stage in stages:
        print(message)
        print("Compose pulls missing service images and builds missing app images; no forced rebuild is requested.")
        service_names = sorted(services or ({"schema-init"} if "schema-init" in args else {"seed"}))
        names = ", ".join(service_names)
        try:
            result = _compose(run, args, values)
        except SetupError as error:
            raise SetupError(
                f"Startup stage for {names} failed: {error} "
                f"Inspect with `docker compose --profile dev ps` and `docker compose --profile dev logs {names}`."
                f"{_recent_service_logs(run, service_names, values)}"
            ) from None
        if result.returncode != 0:
            raise SetupError(
                f"Could not start {names}. Existing database volumes were left intact. "
                f"Inspect with `docker compose --profile dev ps` and `docker compose --profile dev logs {names}`."
                f"{_recent_service_logs(run, service_names, values)}"
            )
        states.update(_wait_healthy(
            run,
            values,
            timeout=COMPOSE_HEALTH_TIMEOUT,
            required_services=services,
            require_schema_init=schema_stage,
            required_completed_services={"seed"} if "seed" in args else set(),
        ))
    return states


def _configure(
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, str]:
    created = not ENV_FILE.exists()
    if created:
        if not ENV_EXAMPLE.is_file():
            raise SetupError("Root .env.example is missing.")
        existing = _parse_env(ENV_EXAMPLE)
        if any(_needs_generated_secret(existing.get(key, "")) for key in LOCAL_SECRET_MINIMUMS):
            _ensure_dev_mysql_volume_absent(run)
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print("Created root .env from .env.example; the file is ignored by Git.")
        updates = _configuration_updates(existing)
        _write_env(ENV_FILE, updates)
    else:
        _check_duplicate_managed_keys(ENV_FILE)

    values = _parse_env(ENV_FILE)
    try:
        _validate_configuration(values)
    except SetupError as error:
        if created:
            raise
        raise SetupError(f"{error} Existing root .env was not changed; edit its values manually and run setup again.") from None
    google_enabled = values.get("GOOGLE_LOGIN_ENABLED", "false").lower() == "true"
    _write_android_google_id(values.get("GOOGLE_CLIENT_ID", "") if google_enabled else "", enabled=google_enabled)
    return values


def main(
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    start_services: bool = True,
) -> int:
    try:
        if sys.version_info < (3, 10):
            raise SetupError("Python 3.10 or newer is required. Install a current Python 3 release and retry.")
        print("1/11 Preparing the backend Python development environment...")
        _ensure_python_environment(run)
        print("2/11 Checking Docker Engine and Compose...")
        _check_docker(run)
        print("3/11 Configuring local integrations...")
        values = _configure(run)
        _check_duplicate_managed_keys(ENV_FILE)
        print("4/11 Validating Docker Compose configuration...")
        result = _compose(run, ["--profile", "dev", "config", "--quiet"], values)
        if result.returncode != 0:
            raise SetupError("Compose configuration is invalid. Review the redacted Compose error above and check root .env values.")
        print("5/11 Checking configured application ports...")
        _check_ports(run, values)
        if not start_services:
            print("Configuration validated. Docker services were not started.")
            return 0
        states = _start_dev_services(run, values)
        print("\nSetup verification:")
        print("MySQL: PASS (healthy)")
        print("Database initialization: PASS (schema-init completed successfully)")
        print(f"Demo seed: {'PASS' if states.get('seed') == 'completed' else 'FAIL'} (preflight and fixture verification completed)")
        for service in ("user-service", "court-service", "booking-service", "payment-service"):
            print(f"{service}: {'PASS' if states.get(service) == 'healthy' else 'FAIL'}")
        gateway_health = _verify_gateway_health(run, values)
        print(f"API Gateway: {'PASS' if all(gateway_health.values()) else 'FAIL'}")
        for path, ok in gateway_health.items():
            print(f"  {path}: {'PASS' if ok else 'FAIL'}")
        print(f"Management Web: {'PASS' if states.get('management-web') == 'healthy' else 'FAIL'}")
        if values.get("SMTP_PROVIDER", "mailpit") == "mailpit" and states.get("mailpit-dev") == "healthy":
            print("Mailpit: PASS (local-only email capture)")
        elif values.get("SMTP_PROVIDER", "mailpit") == "mailpit":
            print("Mailpit: FAIL")
        else:
            print("Mailpit: NOT SELECTED (Gmail is configured; delivery was not tested)")
        if not all(gateway_health.values()):
            failed_paths = ", ".join(path for path, ok in gateway_health.items() if not ok)
            raise SetupError(f"Gateway health verification failed for: {failed_paths}. Inspect service logs before retrying.")

        gateway_host, gateway_port = _effective_service_binding(run, values, "gateway", 8000)
        web_host, web_port = _effective_service_binding(run, values, "management-web", 80)
        mailpit_host, mailpit_port = _effective_service_binding(run, values, "mailpit-dev", 8025)
        gateway_url = f"http://{_format_url_host(_local_url_host(gateway_host))}:{gateway_port}"
        web_url = f"http://{_format_url_host(_local_url_host(web_host))}:{web_port}"
        print("\nSetup complete.")
        print(f"Management Web: {web_url}")
        print(f"API Gateway:    {gateway_url} (docs: {gateway_url}/docs)")
        if values.get("SMTP_PROVIDER", "mailpit") == "mailpit":
            print(f"Mailpit:        http://{_format_url_host(_local_url_host(mailpit_host))}:{mailpit_port} (messages stay local)")
        else:
            print("Gmail SMTP:     configured; live delivery was not tested by setup")
        print("Payment mode:   Mock (no external payment gateway is contacted)")
        if values.get("GOOGLE_LOGIN_ENABLED", "false").lower() == "true":
            print("Google Login:   CONFIGURED; real authentication was not tested")
        else:
            print("Google Login:   DISABLED; email/password sign-in remains available")
        print("To stop services without deleting data: docker compose --profile dev stop")
        return 0
    except SetupError as error:
        print(f"Setup stopped: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
