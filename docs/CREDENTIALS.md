# Credentials and Live-Service Tasks

Most UniClawBench tasks run from packaged files, snapshots, or local services.
A smaller set intentionally exercises authenticated APIs and live
applications. Those tasks declare required environment-variable names in a
task-local `.privacy` file.

## Local Secret File

Fresh clones should create a local privacy file from the committed template:

```bash
cp configs/privacy.example.env configs/privacy.local.env
```

`configs/privacy.local.env` is ignored by git. Put real values there, never in
task YAML, docs, source code, command lines, or committed examples.

The runner loads `.privacy` keys at task start. If a required key is missing,
empty, or still a placeholder, task loading fails before the executor starts.
The executor receives those values as Docker environment variables. The answer
supervisor receives a private copy for grading and leak checks. The public user
simulator never receives credential values.

## Offline vs Live API Mode

Several authenticated tasks ship canonical snapshots in `sources/` so users can
test the runtime without registering third-party accounts.

```dotenv
SNAPSHOT_MODE=1
```

Use `SNAPSHOT_MODE=1` for offline replay when a task supports snapshots. Set a
non-`1` value only when you intentionally want live API calls and have filled
the corresponding credentials. In snapshot mode, live-service credentials
declared beside `SNAPSHOT_MODE` may stay blank and are not injected into the
executor.

## API Keys and Tokens

For static API keys or personal access tokens, copy only the provider values
you need into `configs/privacy.local.env`. Leave unrelated keys blank unless a
task you run declares them.

Common patterns:

- API key plus resource ID, such as a board/base/repository identifier.
- Bot or integration token plus workspace/page/channel identifiers.
- Username/account hint used only to select the correct account.

The exact env-var names are listed in each task's `.privacy` file and in
`configs/privacy.example.env`.

## OAuth Refresh Tokens

OAuth-backed tasks need a local OAuth app or integration controlled by the user.
Create the provider app in the provider's developer console, choose the scopes
required by the task, complete the consent flow locally, and place the resulting
refresh token or serialized token cache in `configs/privacy.local.env`.

The helper below can check or refresh supported local credentials:

```bash
python3 scripts/dev/refresh_tokens.py --check-only
python3 scripts/dev/refresh_tokens.py --provider gcalcli
python3 scripts/dev/refresh_tokens.py --provider zoom
python3 scripts/dev/refresh_tokens.py --provider ncm
```

Use `--no-browser` on headless machines to print the authorization URL instead
of opening it automatically.

## Verification

Before a large run:

1. Run `python3 scripts/dev/check_release_assets.py` to ensure task resources
   are present and LFS assets are materialized.
2. Run one authenticated task with `--fresh` and low parallelism.
3. Inspect the attempt directory for secret leakage:
   result files should contain conclusions and public evidence, not raw tokens,
   passwords, OAuth caches, or private env files.

For public demos and static WebUI exports, prefer tasks with packaged
snapshots or sanitized demo traces unless the live-service credentials are
explicitly part of your local evaluation environment.
