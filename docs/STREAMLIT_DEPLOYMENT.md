# Deploy BatteryFlex on Streamlit Community Cloud

## 1. Sign in

Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with the
GitHub account `deng0529`. Use the workspace for that account.

## 2. Authorise the private repository

Connect GitHub in Community Cloud and grant it access to `deng0529/batteryflex-mvp`.
Keep the GitHub repository private. For private repositories, Community Cloud
uses a read-only GitHub deploy key. Review the app's viewer access separately
from the repository's visibility. [Streamlit private repository access](https://docs.streamlit.io/deploy/streamlit-community-cloud/status)

## 3. Create the app

Choose **Create app** and deploy an existing app with these settings.

| Setting | Value |
| --- | --- |
| Repository | `deng0529/batteryflex-mvp` |
| Branch | `main` |
| Main file path | `app.py` |
| Preferred subdomain | `batteryflex-mvp`, subject to availability |
| Python version | `3.12` |

The root requirements file pins the runtime packages and installs the local
`src` package. SciPy includes HiGHS. The pinned Linux LightGBM wheel requires
`libgomp.so.1`, provided by `libgomp1` in `packages.txt`. The application uses
the JSON subset of YAML and needs no standalone YAML parser. A clean Ubuntu
WSL checkout was tested with CPython 3.12.3, LightGBM 4.7.0, SciPy 1.18.1
and the Debian OpenMP runtime. The app and a small HiGHS solve succeeded. In the clean Linux environment,
Overview loaded all 15 existing production results and rendered both charts
in demo mode. The hosted checklist below applies after deployment.

## 4. Configure secrets

In **Advanced settings**, select Python 3.12 and paste this structure into
**Secrets**, replacing placeholders in Streamlit's settings. The same template
is in [.streamlit/secrets.example.toml](../.streamlit/secrets.example.toml).
[Streamlit deployment settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)

```toml
[batteryflex]
BATTERYFLEX_ACCESS_MODE = "demo"
BATTERYFLEX_STORAGE_MODE = "cloud"
BATTERYFLEX_TURSO_DATABASE_URL = "libsql://batteryflex-mvp-example.turso.io"
BATTERYFLEX_TURSO_AUTH_TOKEN = "replace-with-read-only-database-token"
R2_ACCOUNT_ID = "replace-with-cloudflare-account-id"
BATTERYFLEX_R2_ACCESS_KEY_ID = "replace-with-bucket-scoped-read-only-access-key"
BATTERYFLEX_R2_SECRET_ACCESS_KEY = "replace-with-bucket-scoped-read-only-secret-key"
```

| Key | Requirement and source |
| --- | --- |
| `BATTERYFLEX_ACCESS_MODE` | Set `demo` on every shared deployment. `owner` is for a separate private operator instance or authorised local use. |
| `BATTERYFLEX_STORAGE_MODE` | Set `cloud` on Community Cloud. `local` is for an explicitly bootstrapped development machine. |
| `BATTERYFLEX_TURSO_DATABASE_URL` | Required. Copy the URL of the existing dedicated BatteryFlex database from Turso. |
| `BATTERYFLEX_TURSO_AUTH_TOKEN` | Required. Use a database-scoped read-only token for the existing database, generated in Turso. Owner mode needs a database token with write access. |
| `R2_ACCOUNT_ID` | Required. Copy the account ID from the R2 dashboard. |
| `BATTERYFLEX_R2_ACCESS_KEY_ID` and `BATTERYFLEX_R2_SECRET_ACCESS_KEY` | Required together. Obtain an S3 API credential scoped to bucket `batteryflex-mvp` with Object Read Only access for the demo. A separate owner credential needs Object Read & Write access. |
| `BATTERYFLEX_STORAGE_DIRECTORY` | Optional cache directory on the app host. Leave unset to use the project-local default. The cache is disposable. |

Local loading accepts project `.env`, the `[batteryflex]` secrets section and
environment overrides. Existing `R2_ACCESS_KEY_ID` and
`R2_SECRET_ACCESS_KEY` remain supported as fallbacks. No platform-management
token is needed to run the app. Keep actual credentials in Streamlit Secrets
or a private local environment file.
[R2 bucket-scoped S3 credentials](https://developers.cloudflare.com/r2/api/tokens/)

Demo mode permits saved reads, blocks new training or dispatch before
execution, and rejects SQL mutations and R2 uploads. It is an instance-wide
setting. Set `BATTERYFLEX_ACCESS_MODE=owner` only on an operator instance
whose access is already restricted to authorised viewers, or on your local
machine. Owner mode grants write capability to users who can reach that
instance. The app does not provide individual operator logins.

## 5. Deploy and check logs

Click **Deploy**. Open the app's management panel and inspect build and runtime
logs. Keep the app restricted to reviewers while checking storage and workflow.

## 6. Verify the deployed app

- Open Overview and confirm the SVG and five portfolio indicators. Visit all
  four workspaces and select each of the five historical events.
- Open household demand and Demand Forecasting, confirming measured data and
  saved forecasts load with the intended event date mapping.
- Confirm the active portfolio, then select RBC, MPC and Standalone MILP for
  saved scenarios. Check delivery, objective and charts.
- Open **Dispatch Performance & Evaluation**, choose **All Five Events** and
  **Historical Replay** and check for **15 / 15** compatible scenarios. Inspect
  an individual event as well.
- Verify public visitors can browse without starting work, and that run,
  training and portfolio save actions are unavailable. Check that neither page
  output nor routine logs expose credentials. Restart and verify saved data
  and results load again. Check the logs for import, path and permissions errors.

## 7. Share after review

Use Community Cloud's viewer settings to invite reviewers or change app
visibility once the hosted checks pass. Keep the source repository private
until separately approved.

## Production coverage at release review

The read-only audit verified five historical events, the active default
portfolio, 143,299 household history rows, 15 saved event forecasts and
15 compatible event-only dispatch bundles. It also reopened 32 archived
full-day bundles separately. Production storage was read through the
application's demo boundary.

## Missing demonstration artifacts

Use saved-first recovery only from an authorised local or private owner
instance after approving the production write. Inspect the saved coverage,
load the registered forecast inputs, and use **Run Event Models** only for
missing forecasts. Then use **Run All Five Events** once for each affected
controller with the standard LightGBM, portfolio, and Experiment A defaults.
Saved matches are reused. Repeat read-only coverage verification afterwards.
If household history or the portfolio itself is missing, restore the verified
existing object and metadata references as a separate owner operation.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `ModuleNotFoundError`, invalid entry point, or dependency resolution error | Select `main`, root `app.py` and Python 3.12. Confirm `requirements.txt` is discovered and the editable package install succeeds. |
| LightGBM fails to import `libgomp.so.1` | Confirm `packages.txt` installed `libgomp1` during the Linux build. |
| HiGHS import or solve fails | Confirm the pinned SciPy wheel installed for Python 3.12. Review solve status and input availability before retrying. |
| Turso credentials or schema rejected | Check the dedicated URL, database token, expiry and access to the existing schema. Resolve schema discrepancies on a private owner instance. |
| R2 access or artifact verification fails | Check the account, key scope and matching secret. Confirm the referenced object exists in `batteryflex-mvp`. |
| Saved forecasts or simulations are missing | Verify the active portfolio, source and forecast version, compatible numerical settings, and coverage. Use the owner recovery procedure only if a bundle is genuinely missing. |
| Memory limit or restart | Use the saved-only demo, check dataset and cache sizes, and review Cloud resource logs. Use a separately funded operator environment for model training or heavier work. |
