# Configuration Schemas (Canonical Reference)

Use these schemas for validation (against the JSON versions of your configs). JSONC examples are for humans; strip comments before validating.

## Files and Schemas
- `config/sql_targets.json` — see `config/schemas/sql_targets.schema.json`
- `config/audit_config.json` — see `config/schemas/audit_config.schema.json`
- `config/credentials/*.json` — see `config/schemas/credential.schema.json`

## sql_targets.json (summary)
- `targets` (array, required): list of targets
  - `id` (string, required): unique slug
  - `name` (string, required): display name (Unicode allowed)
  - `server` (string, required)
  - `instance` (string|null)
  - `port` (int|null, default 1433)
  - `auth` (enum: integrated|sql)
  - `username` (string|null)
  - `credential_ref` (string|null)
  - `os_credential_ref` (string|null) — if absent, current process identity is used for OS ops
  - `connect_timeout` (int, default 30)
  - `enabled` (bool, default true)
  - `metadata` (object, optional): `tags` (array<string>), `ip_address` (string), `description` (string)
- `global_settings` (object, optional): `timeout_seconds`, `encrypt_connection`, `trust_server_certificate`

## audit_config.json (summary)
- `organization` (string, required)
- `audit_year` (int, required)
- `audit_date` (string, YYYY-MM-DD, optional)
- `requirements` (object): `minimum_sql_version` (string), `expected_builds` (object<string,string>)
- `output` (object): `directory`, `filename_pattern`, `verbosity`, `include_charts`
- `remediation` (object): `generate_scripts`, `script_format`, `include_rollback`
- `os_remediation` (object): `use_ps_remoting`, `ps_script_path`, `allowed_hosts`
- `performance` (object): `max_parallel_tasks`, `default_timeout_seconds`, `psremoting_timeout_seconds`, `sql_command_timeout_seconds`
- `retry_policy` (object): `max_retries`, `backoff_seconds`
- `logging` (object): `level`, `structured`
- `feature_flags` (object): `enable_fallbacks`, `enable_manual_guidance`
- `os_credentials_ref` (string, optional) — for global OS operations if needed

## credentials/*.json (summary)
- `username` (string) — domain-qualified or plain
- `password` (string)
