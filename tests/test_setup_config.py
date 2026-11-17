from __future__ import annotations

import json
import re
import subprocess

import pytest

import setup_config as setup


def _secrets(monkeypatch):
    monkeypatch.setattr(setup, "getpass", type("HiddenInput", (), {"getpass": staticmethod(lambda _prompt: "")})())


def _configure_paths(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_example = tmp_path / ".env.example"
    env_example.write_text((setup.ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    android_props = tmp_path / "google-oauth.local.properties"
    monkeypatch.setattr(setup, "ENV_FILE", env_file)
    monkeypatch.setattr(setup, "ENV_EXAMPLE", env_example)
    monkeypatch.setattr(setup, "ANDROID_LOCAL_PROPERTIES", android_props)
    monkeypatch.setattr(setup, "_ensure_dev_mysql_volume_absent", lambda *_args, **_kwargs: None)
    return env_file, android_props


def test_default_mailpit_and_google_disabled(monkeypatch, tmp_path):
    env_file, android_props = _configure_paths(monkeypatch, tmp_path)
    _secrets(monkeypatch)
    answers = iter(["", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    values = setup._configure()
    assert values["SMTP_PROVIDER"] == "mailpit"
    assert values["SMTP_HOST"] == "mailpit-dev"
    assert values["SMTP_PORT"] == "1025"
    assert values["SMTP_STARTTLS"] == "false"
    assert values["SMTP_PASSWORD"] == ""
    assert values["GOOGLE_LOGIN_ENABLED"] == "false"
    assert values["GOOGLE_CLIENT_ID"] == ""
    assert env_file.is_file()
    assert set(android_props.read_text(encoding="utf-8").splitlines()) == {
        "GOOGLE_SERVER_CLIENT_ID=", "GOOGLE_LOGIN_ENABLED=false"
    }


def test_mysql_password_is_generated_without_prompt_or_output(monkeypatch, capsys):
    generated = "A" * 32
    prompts = []
    monkeypatch.setattr(setup.secrets, "token_urlsafe", lambda _size: generated)
    monkeypatch.setattr(setup.getpass, "getpass", lambda prompt: prompts.append(prompt) or "")
    answers = iter(["", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    values = setup._configuration_updates()

    assert values["MYSQL_DEV_ROOT_PASSWORD"] == generated
    assert len(values["JWT_SECRET_KEY"]) >= 32
    assert len(values["INTERNAL_SERVICE_TOKEN"]) >= 32
    assert all(set(values[key]) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") for key in setup.LOCAL_SECRET_MINIMUMS)
    assert all("MySQL" not in prompt for prompt in prompts)
    assert not prompts
    assert generated not in capsys.readouterr().out


def test_existing_env_template_is_never_modified_by_setup(monkeypatch, tmp_path, capsys):
    env_file, _ = _configure_paths(monkeypatch, tmp_path)
    env_file.write_text(
        (setup.ROOT / ".env.example").read_text(encoding="utf-8") + "LOCAL_SETTING=keep-this\n",
        encoding="utf-8",
    )
    original = env_file.read_text(encoding="utf-8")
    monkeypatch.setattr(setup.secrets, "token_urlsafe", lambda _size: pytest.fail("existing .env must not generate secrets"))
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("existing .env must not prompt for updates"))
    with pytest.raises(setup.SetupError, match="Existing root .env was not changed"):
        setup._configure(lambda *_args, **_kwargs: pytest.fail("existing .env must not inspect Docker volumes"))
    assert env_file.read_text(encoding="utf-8") == original
    assert "LOCAL_SETTING=keep-this" in original
    assert "B" * 32 not in capsys.readouterr().out


def test_existing_env_missing_required_secret_is_preserved_and_rejected(monkeypatch, tmp_path):
    env_file, _ = _configure_paths(monkeypatch, tmp_path)
    original = (setup.ROOT / ".env.example").read_text(encoding="utf-8")
    original = "\n".join(
        line for line in original.splitlines()
        if not line.startswith("MYSQL_DEV_ROOT_PASSWORD=")
    ) + "\nLOCAL_SETTING=preserve\n"
    env_file.write_text(original, encoding="utf-8")
    monkeypatch.setattr(setup.secrets, "token_urlsafe", lambda _size: pytest.fail("must not generate secrets for existing .env"))
    with pytest.raises(setup.SetupError, match="MYSQL_DEV_ROOT_PASSWORD.*Existing root .env was not changed"):
        setup._configure(lambda *_args, **_kwargs: pytest.fail("existing .env must not inspect Docker volumes"))
    assert env_file.read_text(encoding="utf-8") == original


def test_existing_dev_volume_blocks_password_generation_without_editing_env(monkeypatch, tmp_path):
    volume_guard = setup._ensure_dev_mysql_volume_absent
    env_file, _ = _configure_paths(monkeypatch, tmp_path)
    monkeypatch.setattr(setup, "_ensure_dev_mysql_volume_absent", volume_guard)
    monkeypatch.setattr(setup.secrets, "token_urlsafe", lambda _size: pytest.fail("must not generate with existing volume"))
    command = ["docker", "volume", "ls"]

    def run(actual_command, **_kwargs):
        assert actual_command[:3] == command
        return subprocess.CompletedProcess(actual_command, 0, stdout=f"{setup.DEV_MYSQL_VOLUME}\n", stderr="")

    with pytest.raises(setup.SetupError, match="volume already exists"):
        setup._configure(run)

    assert not env_file.exists()


def test_dev_volume_check_fails_closed_on_docker_error():
    def run(command, **_kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="Docker unavailable")

    with pytest.raises(setup.SetupError, match="Could not check for an existing Dev MySQL volume"):
        setup._ensure_dev_mysql_volume_absent(run)


def test_gmail_path_uses_hidden_app_password_and_validates(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    secret_inputs = iter(["abcd efgh ijkl mnop"])
    monkeypatch.setattr(setup.getpass, "getpass", lambda _prompt: next(secret_inputs))
    answers = iter(["2", "sender@gmail.com", "", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    values = setup._configuration_updates()
    setup._validate_configuration(values)
    assert values["SMTP_PROVIDER"] == "gmail"
    assert values["SMTP_USERNAME"] == "sender@gmail.com"
    assert values["SMTP_PASSWORD"] == "abcdefghijklmnop"
    assert values["SMTP_STARTTLS"] == "true"


def test_google_enabled_requires_real_web_android_ids_and_sha1(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    _secrets(monkeypatch)
    answers = iter([
        "", "2",
        "123456789-example.apps.googleusercontent.com",
        "987654321-android.apps.googleusercontent.com",
        "com.example.sportbooking",
        "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD",
    ])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    values = setup._configuration_updates()
    setup._validate_configuration(values)
    assert values["GOOGLE_LOGIN_ENABLED"] == "true"
    assert "GOOGLE_CLIENT_SECRET" not in values


@pytest.mark.parametrize("web_id,android_id,sha1", [
    ("your-client-id", "987654321-android.apps.googleusercontent.com", "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD"),
    ("123456789-web.apps.googleusercontent.com", "", "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD"),
    ("123456789-web.apps.googleusercontent.com", "987654321-android.apps.googleusercontent.com", ""),
])
def test_google_enable_rejects_missing_or_placeholder_values(monkeypatch, tmp_path, web_id, android_id, sha1):
    _configure_paths(monkeypatch, tmp_path)
    _secrets(monkeypatch)
    responses = ["", "2", web_id, android_id, "com.example.sportbooking", sha1, "1"]
    answers = iter(responses)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    values = setup._configuration_updates()
    assert values["GOOGLE_LOGIN_ENABLED"] == "false"


def test_invalid_google_configuration_can_be_disabled_without_stopping(monkeypatch, tmp_path):
    _configure_paths(monkeypatch, tmp_path)
    _secrets(monkeypatch)
    answers = iter(["", "2", "invalid", "", "com.example.sportbooking", "", "1"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert setup._configuration_updates()["GOOGLE_LOGIN_ENABLED"] == "false"


def test_existing_env_is_kept_and_rerun_does_not_overwrite(monkeypatch, tmp_path):
    env_file, _ = _configure_paths(monkeypatch, tmp_path)
    original = (setup.ROOT / ".env.example").read_text(encoding="utf-8")
    replacements = {
        "MYSQL_DEV_ROOT_PASSWORD=replace_with_a_local_dev_only_password": "MYSQL_DEV_ROOT_PASSWORD=" + "x" * 24,
        "JWT_SECRET_KEY=replace_with_a_random_secret_of_at_least_32_characters": "JWT_SECRET_KEY=" + "y" * 36,
        "INTERNAL_SERVICE_TOKEN=replace_with_a_separate_random_internal_token": "INTERNAL_SERVICE_TOKEN=" + "z" * 36,
    }
    for old, new in replacements.items():
        original = original.replace(old, new)
    original += "LOCAL_NOTE=preserve-me\n"
    env_file.write_text(original, encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    values = setup._configure()
    assert values["LOCAL_NOTE"] == "preserve-me"
    assert env_file.read_text(encoding="utf-8") == original


def test_existing_env_cannot_be_reconfigured_interactively(monkeypatch, tmp_path):
    env_file, _ = _configure_paths(monkeypatch, tmp_path)
    source = (setup.ROOT / ".env.example").read_text(encoding="utf-8")
    source = source.replace("MYSQL_DEV_ROOT_PASSWORD=replace_with_a_local_dev_only_password", "MYSQL_DEV_ROOT_PASSWORD=" + "d" * 24)
    source = source.replace("JWT_SECRET_KEY=replace_with_a_random_secret_of_at_least_32_characters", "JWT_SECRET_KEY=" + "j" * 36)
    source = source.replace("INTERNAL_SERVICE_TOKEN=replace_with_a_separate_random_internal_token", "INTERNAL_SERVICE_TOKEN=" + "i" * 36)
    source += "LOCAL_NOTE=preserve-me\n"
    env_file.write_text(source, encoding="utf-8")
    original = source
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("existing .env must not prompt for configuration changes"))
    values = setup._configure()
    assert values["MYSQL_DEV_ROOT_PASSWORD"] == "d" * 24
    assert values["JWT_SECRET_KEY"] == "j" * 36
    assert values["INTERNAL_SERVICE_TOKEN"] == "i" * 36
    assert values["LOCAL_NOTE"] == "preserve-me"
    assert values["SMTP_PROVIDER"] == "mailpit"
    assert env_file.read_text(encoding="utf-8") == original


def test_validation_rejects_invalid_gmail_and_google_configuration():
    valid = {
        "MYSQL_DEV_ROOT_PASSWORD": "x" * 24,
        "JWT_SECRET_KEY": "y" * 36,
        "INTERNAL_SERVICE_TOKEN": "z" * 36,
        "SMTP_PROVIDER": "gmail",
        "SMTP_USERNAME": "sender@gmail.com",
        "SMTP_PASSWORD": "short",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_STARTTLS": "true",
    }
    with pytest.raises(setup.SetupError, match="Gmail SMTP"):
        setup._validate_configuration(valid)
    valid.update({"SMTP_PROVIDER": "mailpit", "SMTP_USERNAME": "", "SMTP_PASSWORD": "", "SMTP_HOST": "mailpit-dev", "SMTP_PORT": "1025", "SMTP_STARTTLS": "false", "GOOGLE_LOGIN_ENABLED": "true"})
    with pytest.raises(setup.SetupError, match="Web and Android"):
        setup._validate_configuration(valid)


def test_compose_environment_ignores_shell_profile_override(monkeypatch, tmp_path):
    env_file, _ = _configure_paths(monkeypatch, tmp_path)
    env_file.write_text("MYSQL_DEV_ROOT_PASSWORD=dev-local\n", encoding="utf-8")
    monkeypatch.setenv("COMPOSE_PROFILES", "unrequested-profile")
    monkeypatch.setenv("MYSQL_DEV_ROOT_PASSWORD", "shell-override")
    result = setup._compose_environment({"MYSQL_DEV_ROOT_PASSWORD": "dev-local"})
    assert "COMPOSE_PROFILES" not in result
    assert "MYSQL_DEV_ROOT_PASSWORD" not in result


def test_wait_healthy_fails_fast_on_schema_init_error(monkeypatch):
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout='{"Service":"schema-init","State":"exited","ExitCode":1}\n', stderr=""))
    monkeypatch.setattr(setup.time, "sleep", lambda _seconds: None)
    with pytest.raises(setup.SetupError, match="schema initialization failed"):
        setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1)


def test_wait_healthy_schema_failure_includes_redacted_logs(monkeypatch):
    secret = "schema-secret-value"
    def compose(_run, args, _values):
        if "ps" in args:
            output = '{"Service":"schema-init","State":"exited","ExitCode":2}'
        else:
            output = f"initializer failed for mysql://root:{secret}@mysql-dev/db"
        return subprocess.CompletedProcess([], 0, stdout=output, stderr="")
    monkeypatch.setattr(setup, "_compose", compose)
    with pytest.raises(setup.SetupError, match="schema initialization failed") as error:
        setup._wait_healthy(lambda *_args, **_kwargs: None, {"MYSQL_DEV_ROOT_PASSWORD": secret}, timeout=1)
    assert secret not in str(error.value)
    assert "[REDACTED]" in str(error.value)


def test_wait_healthy_rejects_unverifiable_schema_init_exit(monkeypatch):
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout='{"Service":"schema-init","State":"exited"}\n', stderr=""))
    with pytest.raises(setup.SetupError, match="schema-init is exited.*valid ExitCode"):
        setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1)


@pytest.mark.parametrize("record", [
    {"Service": "schema-init", "State": "exited", "ExitCode": 0},
    {"Name": "other-project-schema-init-7", "State": "exited", "ExitCode": 0},
    {"Names": "another-project-schema-init-12", "State": "exited", "ExitCode": 0},
    {"Name": "container-id", "Labels": "com.docker.compose.project=elsewhere,com.docker.compose.service=schema-init", "State": "exited", "ExitCode": 0},
])
def test_wait_healthy_recognizes_schema_completion_across_compose_formats(monkeypatch, record):
    output = json.dumps(record) + "\n"
    monkeypatch.setattr(setup, "_compose", lambda _run, args, _values: (
        subprocess.CompletedProcess([], 0, stdout=output, stderr="")
        if "ps" in args else subprocess.CompletedProcess([], 0, stdout="", stderr="")
    ))
    result = setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1, required_services=set())
    assert result["schema-init"] == "completed"


def test_compose_record_parser_accepts_service_name_without_fixed_project_or_replica():
    assert setup._compose_record_service({"Name": "my-local-schema-init-19"}) == "schema-init"


def test_wait_healthy_keeps_waiting_while_schema_init_is_running(monkeypatch):
    records = iter([
        '{"Service":"schema-init","State":"running"}\n',
        '{"Service":"schema-init","State":"exited","ExitCode":0}\n',
    ])
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout=next(records), stderr=""))
    monkeypatch.setattr(setup.time, "sleep", lambda _seconds: None)
    assert setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=2, required_services=set())["schema-init"] == "completed"


def test_wait_healthy_polls_until_slow_mysql_becomes_healthy(monkeypatch):
    now = [0.0]
    outputs = iter([
        '{"Service":"mysql-dev","State":"running","Health":"starting"}',
        '{"Service":"mysql-dev","State":"running","Health":"healthy"}',
    ])
    monkeypatch.setattr(setup.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(setup.time, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout=next(outputs), stderr=""))
    states = setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=30, required_services={"mysql-dev"}, require_schema_init=False)
    assert states["mysql-dev"] == "healthy"
    assert now[0] == setup.HEALTH_POLL_INTERVAL


def test_wait_healthy_missing_schema_record_fails_clearly(monkeypatch):
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout="", stderr=""))
    with pytest.raises(setup.SetupError, match="no container record.*schema-init"):
        setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1)


def test_wait_healthy_malformed_json_fails_clearly(monkeypatch):
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout="{broken\n", stderr=""))
    with pytest.raises(setup.SetupError, match="Could not parse.*JSON"):
        setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1)


def test_wait_healthy_timeout_reports_pending_service_logs(monkeypatch):
    calls = []
    def compose(_run, args, _values):
        calls.append(args)
        if "ps" in args:
            rows = [
                {"Service": "mysql-dev", "State": "running", "Health": "healthy"},
                {"Service": "mailpit-dev", "State": "running", "Health": "healthy"},
                {"Service": "gateway", "State": "running", "Health": "starting"},
            ]
            return subprocess.CompletedProcess([], 0, stdout="\n".join(json.dumps(row) for row in rows), stderr="")
        return subprocess.CompletedProcess([], 0, stdout="gateway startup detail", stderr="")
    now = [0.0]
    monkeypatch.setattr(setup.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(setup.time, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))
    monkeypatch.setattr(setup, "_compose", compose)
    with pytest.raises(setup.SetupError, match="(?s)gateway=running/starting.*Recent gateway logs"):
        setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1, required_services={"gateway"}, require_schema_init=False)
    assert any("logs" in args and args[-1] == "gateway" for args in calls)


def test_main_starts_dev_services_in_stages_without_android_prompt(monkeypatch, capsys):
    calls = []
    values = {
        "MYSQL_DEV_ROOT_PASSWORD": "d" * 24,
        "JWT_SECRET_KEY": "j" * 36,
        "INTERNAL_SERVICE_TOKEN": "i" * 36,
        "SMTP_PROVIDER": "mailpit",
        "SMTP_HOST": "mailpit-dev",
        "SMTP_PORT": "1025",
        "SMTP_STARTTLS": "false",
        "GOOGLE_LOGIN_ENABLED": "false",
    }
    monkeypatch.setattr(setup, "_check_docker", lambda _run: None)
    monkeypatch.setattr(setup, "_ensure_python_environment", lambda _run: None)
    monkeypatch.setattr("builtins.input", lambda *_args: pytest.fail("setup must not prompt for Android configuration"))
    monkeypatch.setattr(setup, "_check_ports", lambda *_args: None)
    monkeypatch.setattr(setup, "_configure", lambda *_args: values)
    monkeypatch.setattr(setup, "_wait_healthy", lambda *_args, **_kwargs: {
        "user-service": "healthy", "court-service": "healthy", "booking-service": "healthy",
        "payment-service": "healthy", "management-web": "healthy", "mailpit-dev": "healthy",
        "schema-init": "completed", "seed": "completed",
    })
    monkeypatch.setattr(setup, "_verify_gateway_health", lambda *_args, **_kwargs: {"/health": True})
    monkeypatch.setattr(setup, "_effective_service_binding", lambda _run, _values, service, _target: (
        "127.0.0.1", {"gateway": 8000, "management-web": 8080, "mailpit-dev": 8025}[service]
    ))

    def compose(_run, args, _values):
        calls.append(list(args))
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    monkeypatch.setattr(setup, "_compose", compose)
    result = setup.main(run=lambda *_args, **_kwargs: None, start_services=True)
    assert result == 0
    assert calls[0] == ["--profile", "dev", "config", "--quiet"]
    assert calls[1:] == [
        ["--profile", "dev", "up", "-d", "mysql-dev", "mailpit-dev"],
        ["--profile", "dev", "up", "-d", "schema-init"],
        ["--profile", "dev", "up", "-d", "user-service", "court-service", "booking-service", "payment-service"],
        ["--profile", "dev", "up", "-d", "seed"],
        ["--profile", "dev", "up", "-d", "gateway"],
        ["--profile", "dev", "up", "-d", "management-web"],
    ]
    output = capsys.readouterr().out
    assert "Android API configuration" not in output
    assert "LAN IPv4" not in output


def test_gateway_health_checks_all_proxied_services_on_compose_port(monkeypatch):
    output = json.dumps({"services": {"gateway": {"ports": [
        {"host_ip": "127.0.0.1", "published": "18000", "target": 8000},
    ]}}})
    monkeypatch.setattr(setup, "_compose", lambda *_args: subprocess.CompletedProcess([], 0, stdout=output, stderr=""))
    requested = []

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return False

    def request(url, timeout):
        requested.append((url, timeout))
        return Response()

    result = setup._verify_gateway_health(lambda *_args: None, {}, request=request)

    assert len(result) == 5 and all(result.values())
    assert all(url.startswith("http://127.0.0.1:18000/") for url, _timeout in requested)


def test_gateway_health_failure_is_reported_per_endpoint(monkeypatch):
    output = json.dumps({"services": {"gateway": {"ports": [
        {"published": "8000", "target": 8000},
    ]}}})
    monkeypatch.setattr(setup, "_compose", lambda *_args: subprocess.CompletedProcess([], 0, stdout=output, stderr=""))
    result = setup._verify_gateway_health(lambda *_args: None, {}, request=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    assert len(result) == 5 and not any(result.values())


def test_numbered_choice_retries_invalid_text_and_out_of_range_then_accepts_number(monkeypatch, capsys):
    answers = iter([" mailpit ", "3", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert setup._choice("Email configuration", ("mailpit", "gmail"), "mailpit") == "gmail"
    output = capsys.readouterr().out
    assert "[1] Mailpit (Recommended)" in output
    assert "[2] Gmail SMTP" in output
    assert output.count("Invalid choice") == 2


@pytest.mark.parametrize(("answer", "expected"), [("", "mailpit"), ("1", "mailpit"), ("2", "gmail")])
def test_numbered_choice_defaults_and_selects_each_email_option(monkeypatch, answer, expected):
    monkeypatch.setattr("builtins.input", lambda _prompt: answer)
    assert setup._choice("Email configuration", ("mailpit", "gmail"), "mailpit") == expected


def test_setup_no_longer_mentions_or_writes_android_api_configuration():
    source = (setup.ROOT / "setup_config.py").read_text(encoding="utf-8")
    assert "LAN IPv4" not in source
    assert "api.local.properties" not in source
    assert "_configure_android_api" not in source
    assert "_write_android_api_url" not in source


def test_gradle_default_is_single_source_and_retrofit_uses_build_config():
    gradle = (setup.ROOT / "android-user/app/build.gradle.kts").read_text(encoding="utf-8")
    retrofit = (setup.ROOT / "android-user/app/src/main/java/com/example/sportbooking/api/ApiClient.java").read_text(encoding="utf-8")
    assert 'project.findProperty("API_BASE_URL")?.toString()' in gradle
    assert len(re.findall(r'configuredGatewayUrl\s*=.*?\?:\s*"https?://[^"\s]+/"', gradle, re.DOTALL)) == 1
    assert "api.local.properties" not in gradle
    assert '"API_BASE_URL"' in gradle
    assert ".baseUrl(BuildConfig.API_BASE_URL)" in retrofit


def test_setup_launchers_still_use_shared_helper():
    assert "setup_config.py" in (setup.ROOT / "setup.bat").read_text(encoding="utf-8")
    assert "setup_config.py" in (setup.ROOT / "setup.sh").read_text(encoding="utf-8")


def test_fresh_python_environment_creates_venv_and_installs_dev_requirements(monkeypatch, tmp_path):
    venv_dir = tmp_path / "backend" / ".venv"
    marker = venv_dir / ".requirements-dev.sha256"
    python = tmp_path / "backend" / ".venv" / "Scripts" / "python.exe"
    calls = []
    monkeypatch.setattr(setup, "VENV_DIR", venv_dir)
    monkeypatch.setattr(setup, "VENV_REQUIREMENTS_MARKER", marker)
    monkeypatch.setattr(setup, "RUNTIME_REQUIREMENTS", setup.ROOT / "backend" / "requirements.txt")
    monkeypatch.setattr(setup, "DEV_REQUIREMENTS", setup.ROOT / "backend" / "requirements-dev.txt")
    monkeypatch.setattr(setup, "_venv_python", lambda: python)

    def run(command, **_kwargs):
        calls.append(command)
        if command[1:3] == ["-m", "venv"]:
            python.parent.mkdir(parents=True)
            python.touch()
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    setup._ensure_python_environment(run, confirm_repair=lambda *_args: True)
    assert calls[0][1:3] == ["-m", "venv"]
    assert calls[1][1:4] == ["-m", "pip", "install"]
    assert calls[1][-2:] == ["-r", str(setup.DEV_REQUIREMENTS)]
    assert marker.is_file()


def test_valid_python_environment_is_reused_without_install(monkeypatch, tmp_path):
    venv_dir = tmp_path / ".venv"
    python = venv_dir / "Scripts" / "python.exe"
    venv_dir.mkdir()
    python.parent.mkdir()
    python.touch()
    monkeypatch.setattr(setup, "VENV_DIR", venv_dir)
    marker = venv_dir / ".requirements-dev.sha256"
    monkeypatch.setattr(setup, "VENV_REQUIREMENTS_MARKER", marker)
    monkeypatch.setattr(setup, "_venv_python", lambda: python)
    monkeypatch.setattr(setup, "RUNTIME_REQUIREMENTS", setup.ROOT / "backend" / "requirements.txt")
    monkeypatch.setattr(setup, "DEV_REQUIREMENTS", setup.ROOT / "backend" / "requirements-dev.txt")
    marker.write_text(setup._requirements_fingerprint(), encoding="ascii")
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    setup._ensure_python_environment(run, confirm_repair=lambda *_args: pytest.fail("valid venv prompted for repair"))
    assert len(calls) == 2
    assert all("install" not in command for command in calls)


def test_dependency_install_failure_stops_and_preserves_venv(monkeypatch, tmp_path):
    venv_dir = tmp_path / ".venv"
    python = venv_dir / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    marker = venv_dir / ".requirements-dev.sha256"
    monkeypatch.setattr(setup, "VENV_DIR", venv_dir)
    monkeypatch.setattr(setup, "VENV_REQUIREMENTS_MARKER", marker)
    monkeypatch.setattr(setup, "_venv_python", lambda: python)
    monkeypatch.setattr(setup, "RUNTIME_REQUIREMENTS", setup.ROOT / "backend" / "requirements.txt")
    monkeypatch.setattr(setup, "DEV_REQUIREMENTS", setup.ROOT / "backend" / "requirements-dev.txt")
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        if "install" in command:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="index unavailable")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with pytest.raises(setup.SetupError, match="dependency installation failed"):
        setup._ensure_python_environment(run, confirm_repair=lambda *_args: True)
    assert python.is_file()
    assert not marker.exists()
    assert any("install" in command for command in calls)


def _port_compose(monkeypatch, config_ports, ps_output=""):
    outputs = iter([
        subprocess.CompletedProcess([], 0, stdout=json.dumps({"services": config_ports}), stderr=""),
        subprocess.CompletedProcess([], 0, stdout=ps_output, stderr=""),
    ])
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: next(outputs))


def test_port_check_uses_effective_default_ports_when_free(monkeypatch):
    _port_compose(monkeypatch, {
        "gateway": {"ports": [{"published": "8000"}]},
        "management-web": {"ports": [{"published": "8080"}]},
        "mailpit-dev": {"ports": [{"published": "1025"}, {"published": "8025"}]},
    })
    monkeypatch.setattr(setup.socket, "socket", lambda *_args: _FakeSocket())
    setup._check_ports(lambda *_args, **_kwargs: None, {})


def test_port_check_uses_custom_gateway_port(monkeypatch):
    _port_compose(monkeypatch, {"gateway": {"ports": [{"published": "18000"}]}})
    monkeypatch.setattr(setup.socket, "socket", lambda *_args: _FakeSocket())
    setup._check_ports(lambda *_args, **_kwargs: None, {})


class _FakeSocket:
    def bind(self, address):
        self.address = address

    def close(self):
        pass


class _BusySocket(_FakeSocket):
    def bind(self, address):
        raise OSError("busy")


def test_port_check_allows_port_reported_by_this_compose_project(monkeypatch):
    _port_compose(monkeypatch, {"gateway": {"ports": [{"published": "8000"}]}},
                  '{"Service":"gateway","State":"running","Publishers":[{"PublishedPort":8000,"TargetPort":8000}]}')
    monkeypatch.setattr(setup.socket, "socket", lambda *_args: _BusySocket())
    setup._check_ports(lambda *_args, **_kwargs: None, {})


def test_port_check_rejects_unrelated_port_owner(monkeypatch):
    _port_compose(monkeypatch, {"gateway": {"ports": [{"published": "18000"}]}})
    monkeypatch.setattr(setup.socket, "socket", lambda *_args: _BusySocket())
    with pytest.raises(setup.SetupError, match="unrelated process or project.*18000"):
        setup._check_ports(lambda *_args, **_kwargs: None, {})


def test_google_package_mismatch_is_not_accepted(monkeypatch):
    _secrets(monkeypatch)
    answers = iter(["", "2", "123456789-web.apps.googleusercontent.com", "987654321-android.apps.googleusercontent.com", "com.other.app", "", "1"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    values = setup._configuration_updates()
    assert values["GOOGLE_LOGIN_ENABLED"] == "false"
    assert values["GOOGLE_ANDROID_PACKAGE_NAME"] == setup.ANDROID_PACKAGE_NAME


def test_existing_invalid_google_settings_fail_without_editing_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    android_properties = tmp_path / "google-oauth.local.properties"
    env_file.write_text(
        "MYSQL_DEV_ROOT_PASSWORD=" + "d" * 24 + "\n" +
        "JWT_SECRET_KEY=" + "j" * 36 + "\n" +
        "INTERNAL_SERVICE_TOKEN=" + "i" * 36 + "\n" +
        "SMTP_PROVIDER=mailpit\nSMTP_HOST=mailpit-dev\nSMTP_PORT=1025\nSMTP_STARTTLS=false\n" +
        "GOOGLE_LOGIN_ENABLED=true\nGOOGLE_CLIENT_ID=\nGOOGLE_ANDROID_CLIENT_ID=\n" +
        "GOOGLE_ANDROID_PACKAGE_NAME=com.example.sportbooking\nGOOGLE_ANDROID_SHA1=\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(setup, "ENV_FILE", env_file)
    monkeypatch.setattr(setup, "ANDROID_LOCAL_PROPERTIES", android_properties)
    original = env_file.read_text(encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: pytest.fail("existing .env must not prompt to disable Google"))
    with pytest.raises(setup.SetupError, match="Google Login.*Existing root .env was not changed"):
        setup._configure(run=lambda *_args, **_kwargs: pytest.fail("existing .env must not inspect Docker volumes"))
    assert env_file.read_text(encoding="utf-8") == original


def test_google_configuration_validation_rejects_wrong_android_package():
    values = {
        "MYSQL_DEV_ROOT_PASSWORD": "d" * 24,
        "JWT_SECRET_KEY": "j" * 36,
        "INTERNAL_SERVICE_TOKEN": "i" * 36,
        "SMTP_PROVIDER": "mailpit", "SMTP_HOST": "mailpit-dev", "SMTP_PORT": "1025",
        "SMTP_STARTTLS": "false", "GOOGLE_LOGIN_ENABLED": "true",
        "GOOGLE_CLIENT_ID": "123456789-web.apps.googleusercontent.com",
        "GOOGLE_ANDROID_CLIENT_ID": "987654321-android.apps.googleusercontent.com",
        "GOOGLE_ANDROID_PACKAGE_NAME": "com.other.app",
        "GOOGLE_ANDROID_SHA1": "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD",
    }
    with pytest.raises(setup.SetupError, match="package name"):
        setup._validate_configuration(values)


@pytest.mark.parametrize("key", ["SMTP_PASSWORD", "GOOGLE_CLIENT_ID", "USER_DATABASE_URL"])
def test_duplicate_managed_env_key_fails_without_showing_value(tmp_path, key):
    secret = "secret-value-do-not-print"
    env = tmp_path / ".env"
    env.write_text(f"{key}={secret}\n{key}=second-value\n", encoding="utf-8")
    with pytest.raises(setup.SetupError) as error:
        setup._check_duplicate_managed_keys(env)
    assert key in str(error.value)
    assert secret not in str(error.value)


def test_wait_healthy_fails_fast_on_exited_backend_and_redacts_logs(monkeypatch):
    values = {"MYSQL_DEV_ROOT_PASSWORD": "secret-password"}
    responses = iter([
        subprocess.CompletedProcess([], 0, stdout='{"Service":"court-service","State":"exited","ExitCode":1}\n', stderr=""),
        subprocess.CompletedProcess([], 0, stdout="startup mysql://root:secret-password@mysql-dev:3306/db\n", stderr=""),
    ])
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: next(responses))
    with pytest.raises(setup.SetupError, match="court-service.*exited") as error:
        setup._wait_healthy(lambda *_args, **_kwargs: None, values, timeout=2)
    assert "secret-password" not in str(error.value)
    assert "[REDACTED]" in str(error.value)


@pytest.mark.parametrize("state", ["restarting", "exited"])
def test_wait_healthy_fails_fast_on_restarting_or_exited_container(monkeypatch, state):
    responses = iter([
        subprocess.CompletedProcess([], 0, stdout=json.dumps({"Service": "booking-service", "State": state}), stderr=""),
        subprocess.CompletedProcess([], 0, stdout="initializer failed", stderr=""),
    ])
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: next(responses))
    with pytest.raises(setup.SetupError, match="booking-service"):
        setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=2)


def test_wait_healthy_fails_fast_on_unhealthy_container(monkeypatch):
    responses = iter([
        subprocess.CompletedProcess([], 0, stdout='{"Service":"gateway","State":"running","Health":"unhealthy"}\n', stderr=""),
        subprocess.CompletedProcess([], 0, stdout="gateway health check failed", stderr=""),
    ])
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: next(responses))
    with pytest.raises(setup.SetupError, match="gateway.*unhealthy"):
        setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=2, required_services={"gateway"}, require_schema_init=False)


def test_compose_start_timeout_is_finite_and_redacts_output(monkeypatch, capsys):
    secret = "local-docker-password"
    monkeypatch.setattr(setup, "_compose_environment", lambda _values: {})

    def timed_out(command, **kwargs):
        assert kwargs["timeout"] == setup.COMPOSE_COMMAND_TIMEOUT
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=f"MYSQL_ROOT_PASSWORD={secret}")

    with pytest.raises(setup.SetupError, match=f"timed out after {setup.COMPOSE_COMMAND_TIMEOUT} seconds") as error:
        setup._compose(timed_out, ["--profile", "dev", "up", "-d"], {"MYSQL_DEV_ROOT_PASSWORD": secret})
    assert secret not in str(error.value)
    assert secret not in capsys.readouterr().err


def test_wait_healthy_returns_when_all_services_are_healthy(monkeypatch):
    records = [{"Service": name, "State": "running", "Health": "healthy"} for name in setup.HEALTHY_SERVICES]
    records.append({"Service": "schema-init", "State": "exited", "ExitCode": 0})
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout="\n".join(json.dumps(r) for r in records), stderr=""))
    setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=2)


def test_wait_healthy_recognizes_successful_seed_one_shot(monkeypatch):
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess(
        [], 0, stdout='{"Service":"seed","State":"exited","ExitCode":0}\n', stderr=""
    ))
    states = setup._wait_healthy(
        lambda *_args, **_kwargs: None, {}, timeout=1,
        required_services=set(), require_schema_init=False,
        required_completed_services={"seed"},
    )
    assert states["seed"] == "completed"


@pytest.mark.parametrize(
    ("container_name", "expected"),
    [
        ("another-project-seed-1", "seed"),
        ("another-project-seed-2", "seed"),
        ("another-project-schema-init-1", "schema-init"),
        ("another-project-user-service-3", "user-service"),
    ],
)
def test_compose_record_service_name_fallback(container_name, expected):
    assert setup._compose_record_service({"Name": container_name}) == expected


def test_mysql_healthcheck_window_matches_setup_health_timeout():
    compose = (setup.ROOT / "compose.yaml").read_text(encoding="utf-8")
    mysql_service = compose.split("  mysql-dev:", 1)[1].split("  mailpit-dev:", 1)[0]
    assert "interval: 5s" in mysql_service
    assert "retries: 132" in mysql_service
    assert "start_period: 60s" in mysql_service
    assert setup.COMPOSE_HEALTH_TIMEOUT == 720


def test_wait_healthy_seed_failure_reports_seed_logs(monkeypatch):
    responses = iter([
        subprocess.CompletedProcess([], 0, stdout='{"Service":"seed","State":"exited","ExitCode":7}\n', stderr=""),
        subprocess.CompletedProcess([], 0, stdout="preflight conflict in Task 4 fixtures", stderr=""),
    ])
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: next(responses))
    with pytest.raises(setup.SetupError, match="(?s)demo seed failed.*Recent seed logs") as error:
        setup._wait_healthy(
            lambda *_args, **_kwargs: None, {}, timeout=1,
            required_services=set(), require_schema_init=False,
            required_completed_services={"seed"},
        )
    assert "preflight conflict in Task 4 fixtures" in str(error.value)


@pytest.mark.parametrize("health,expected", [("healthy", True), ("unhealthy", False)])
def test_wait_healthy_handles_fast_and_slow_mysql_health(monkeypatch, health, expected):
    monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess(
        [], 0, stdout=json.dumps({"Service": "mysql-dev", "State": "running", "Health": health}), stderr=""
    ))
    monkeypatch.setattr(setup.time, "sleep", lambda _seconds: None)
    if expected:
        assert setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1, required_services={"mysql-dev"}, require_schema_init=False)["mysql-dev"] == "healthy"
    else:
        monkeypatch.setattr(setup, "_compose", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout=json.dumps({"Service": "mysql-dev", "State": "running", "Health": "unhealthy"}), stderr="") if "ps" in _args[1] else subprocess.CompletedProcess([], 0, stdout="mysql healthcheck failure", stderr=""))
        with pytest.raises(setup.SetupError, match="mysql-dev.*unhealthy"):
            setup._wait_healthy(lambda *_args, **_kwargs: None, {}, timeout=1, required_services={"mysql-dev"}, require_schema_init=False)


def test_schema_completion_is_required_before_backend_stage(monkeypatch):
    stages = []
    def compose(_run, args, _values):
        if "up" in args:
            stages.append(tuple(args[4:]))
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    monkeypatch.setattr(setup, "_compose", compose)
    def wait(_run, _values, **kwargs):
        if kwargs.get("require_schema_init"):
            raise setup.SetupError("schema init did not complete")
        return {}
    monkeypatch.setattr(setup, "_wait_healthy", wait)
    with pytest.raises(setup.SetupError, match="schema init did not complete"):
        setup._start_dev_services(lambda *_args, **_kwargs: None, {})
    assert stages == [("mysql-dev", "mailpit-dev"), ("schema-init",)]


def test_seed_stage_failure_blocks_gateway_and_management_web(monkeypatch):
    stages = []
    def compose(_run, args, _values):
        if "up" in args:
            stages.append(tuple(args[4:]))
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    monkeypatch.setattr(setup, "_compose", compose)
    def wait(_run, _values, **kwargs):
        if kwargs.get("required_completed_services") == {"seed"}:
            raise setup.SetupError("Development demo seed failed")
        return {}
    monkeypatch.setattr(setup, "_wait_healthy", wait)
    with pytest.raises(setup.SetupError, match="demo seed failed"):
        setup._start_dev_services(lambda *_args, **_kwargs: None, {})
    assert stages == [
        ("mysql-dev", "mailpit-dev"), ("schema-init",),
        ("user-service", "court-service", "booking-service", "payment-service"),
        ("seed",),
    ]
