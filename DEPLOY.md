# Deploying BUNYAN AI (club demo)

One Docker image runs everything: the production React frontend, the FastAPI backend,
the five agents, and Node.js with Playwright Chromium for the real QA Tester. The
frontend and the API share one origin, so there is no CORS setup and one HTTPS address.

```
browser ──HTTPS──► platform edge (TLS) ──► container :$PORT
                                            uvicorn (non-root "bunyan")
                                            ├─ /            React app (frontend-dist)
                                            ├─ /projects/…  API, artifacts, preview, ZIP
                                            ├─ /health      health check (no login)
                                            └─ QA: Playwright Chromium on 127.0.0.1 only
                                            /data  projects + generated files (volume)
```

## Security for a shared demo

| Control | How |
|---|---|
| Login on every route (API, artifacts, preview, download, the app itself) | HTTP Basic with `BUNYAN_USERS`, checked in the backend. Only `/health` is open. CORS is not used as access control. |
| Testers cannot see each other's projects | Each project stores its `owner`; anyone else gets 404 on every route. |
| Password guessing | 10 failures per address in 5 minutes, then 429. Passwords are stored as PBKDF2-SHA256 hashes. |
| Request and generation limits | Per user: write requests per minute, projects per day, analyses per day. All users: real-LLM analyses per day, analyses at the same time. Counters survive restarts (`/data/usage.json`). |
| Anthropic spending | One paid request per analysis (`BA_MAX_RETRIES=0`, `BA_SDK_MAX_RETRIES=0`, `BA_FALLBACKS=off`), `BA_MAX_TOKENS=32000` (at most about $0.68 per request on claude-opus-5-5), and the daily cap above. Also set a monthly spend limit on the key's workspace in the Anthropic Console. |
| Secrets | Only as platform variables at runtime. Nothing in the image or the frontend bundle (`.dockerignore` excludes `.env` files). The QA process that runs generated code gets an environment without the API key or the user list. |
| Generated app preview | Served with `Content-Security-Policy: sandbox …` (opaque origin, even in its own tab): it cannot read this site's storage or cookies, script the page around it, or make network requests. Records live in memory there; the downloaded ZIP uses localStorage normally. |
| Generated code and QA | Generated apps are the fixed template filled with escaped JSON (no `innerHTML`). QA serves them on 127.0.0.1 inside the container and runs one QA at a time. |
| Container | Non-root user (uid 10001); the entrypoint only fixes `/data` ownership, then drops privileges. Compose drops all other capabilities, sets `no-new-privileges`, 2 GB RAM, 2 CPUs, 512 processes. |
| Paths | Project ids are UUIDs; artifact and preview names come from a fixed list and are resolved inside the project folder. |

## Guest mode (no login)

`BUNYAN_AUTH=guest` lets visitors start without a login, with the same server-side checks:

- On the first request the server issues an anonymous guest identity: 24 random bytes from
  `secrets`, with its issue time, signed with HMAC-SHA256 (`BUNYAN_SESSION_SECRET`), in a cookie
  that is `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, 7 days. A changed, forged or expired
  cookie is replaced by a new, empty guest.
- Each guest is its own owner: other guests get 404 on every route. Guests never see projects
  made in login mode.
- Limits: `BUNYAN_MAX_PROJECTS_PER_USER_PER_DAY` per guest (3 for the club), plus per address
  (`BUNYAN_MAX_PROJECTS_PER_IP_PER_DAY`, new guest cookies per hour, write requests per minute)
  and for the whole site (`BUNYAN_MAX_PROJECTS_PER_DAY`), so clearing cookies cannot buy
  unlimited projects. A whole club on one Wi-Fi shares one address: size the per-address limits for it.
- Writes from another site are refused (Origin check, plus SameSite).
- Guest mode refuses to start unless `BA_MODE=mock`: anonymous visitors never cause paid requests.
- The public site (the React app and its files) always loads: only the API (`/projects…`) needs a
  new guest identity, so a busy shared Wi-Fi never locks people out of the homepage. Errors opened in a
  browser are a small Arabic page in the Riyadh theme; API errors are JSON with `charset=utf-8`.
- Rollback: set `BUNYAN_AUTH=required` again (the `BUNYAN_USERS` logins still work).

## Run locally (Docker Compose)

```bash
cp deploy.env.example deploy.env
python3 -m backend.security hash-password ghala     # prints ghala:pbkdf2:…
# put the printed line(s) into BUNYAN_USERS in deploy.env, comma separated
docker compose up --build -d
docker compose ps                                     # STATUS shows (healthy)
open http://localhost:8080                            # the browser asks for the login
```

Data stays in the `bunyan-data` volume across `docker compose restart` and `down`/`up`
(`docker compose down -v` deletes it).

## Deploy on Railway

1. Create a project and a service. The live demo is deployed by upload from a checkout of
   `deploy/club-demo` (`railway up --detach`); it is not linked to GitHub, so pushing a branch never
   changes the live site. Railway builds the `Dockerfile` (see `railway.json`, health check `/health`).
2. Add a volume to the service, mounted at `/data`.
3. Service variables: everything from `deploy.env.example` with real values. Put
   `BUNYAN_USERS` and, for real analysis, `ANTHROPIC_API_KEY` as variables there (never in git).
4. Settings, Networking: generate a public domain (`https://<name>.up.railway.app`).
5. Check: `curl https://<name>.up.railway.app/health` returns `{"status":"ok"}`; in guest mode the
   homepage opens without a login, with `BUNYAN_AUTH=required` it asks for one.
6. Rollback: Deployments → redeploy an earlier successful deployment (volume and variables stay).

Size the service at 2 GB RAM (Chromium for QA plus the backend). Hobby plan: $5/month
including $5 of usage; usage is about $10 per GB of RAM and $20 per vCPU per month.

## Protected real Business Analyst for guests (optional)

Keep `BUNYAN_AUTH=guest` and `BA_MODE=mock`, then set `BUNYAN_LLM_ACCESS=codes` with
`BUNYAN_LLM_ACCESS_CODES` (hashed: `python -m backend.security hash-password <label>`),
`BA_LLM_PROVIDER=anthropic`, `BA_LLM_MODEL=claude-opus-5-5`, `BA_LLM_BACKEND=direct`,
`BA_MAX_RETRIES=0`, `BA_SDK_MAX_RETRIES=0`, `BA_FALLBACKS=off`, `BA_MAX_TOKENS=32000` and the
`ANTHROPIC_API_KEY` secret. Limits: `BUNYAN_LLM_MAX_PER_CODE_PER_DAY` (3),
`BUNYAN_MAX_LLM_ANALYSES_PER_DAY`, `BUNYAN_MAX_CONCURRENT_ANALYSES`, `BUNYAN_LLM_DAILY_BUDGET_USD` (2;
each request reserves its worst case, 0.72 USD, before it is sent, then books the real usage).
The server refuses to start with a weaker setting. Visitors without a code keep the mock analyst.
Also set a monthly spend limit for the key's workspace in the Anthropic Console.

### Cumulative experiment budget (required with access codes)

`BUNYAN_TOTAL_LLM_BUDGET_USD` (for example `5.00`) is the total for the whole experiment, across analyses and AI repairs. It is never reset. `BUNYAN_LLM_BUDGET_STARTING_SPENT_USD` must also be set: what was already spent, decided by the lead. Without either variable, paid requests are refused.

The ledger is `/data/llm_budget.json` (keep the volume). Do not delete it or `llm_budget.initialized`; a missing or damaged ledger blocks paid requests until a person fixes it. Optional:
- `BUNYAN_LLM_MAX_ANALYSES_PER_CODE_TOTAL`: a per-code cap for the experiment;
- `BUNYAN_ADMINS=ghala`, for `GET /admin/llm-budget` with that user's login.

Details: [docs/AI-RELEASE-PLAN.md](docs/AI-RELEASE-PLAN.md).

## Repair loop

`BUNYAN_REPAIR=restore` (default) runs at most two deterministic repairs with a real QA re-test after
each real change; `off` disables it. No LLM and no cost.

`BUNYAN_REPAIR=llm` (experimental, needs `BUNYAN_LLM_ACCESS=codes`): restore first, then, for a
project whose owner entered an access code, one bounded Claude request proposes find/replace edits
to `index.html`, `style.css` or `app.js` only; they are validated before anything is written and QA
re-tests in Chromium. Limit: `BUNYAN_LLM_REPAIRS_PER_CODE_PER_DAY` (3), the same daily USD budget,
and `BUNYAN_LLM_REPAIR_TIMEOUT` seconds per request (120). Settings, procedures and staged release:
[docs/AI-RELEASE-PLAN.md](docs/AI-RELEASE-PLAN.md).

## Switching on the real Business Analyst

Set `BA_MODE=llm`, `BA_LLM_PROVIDER=anthropic`, `BA_LLM_MODEL=claude-opus-5-5`,
`BA_LLM_BACKEND=direct` and the `ANTHROPIC_API_KEY` secret, then redeploy. The backend
logs `Business Analyst: LLM mode (...)` at startup and one `BA model call:` line with the
token usage for each paid request. With `BA_MODE=mock` no request reaches Anthropic.

## Tester instructions

Guest mode (the live demo): open the address; no login. Arabic guide: [docs/user-guide-ar.md](docs/user-guide-ar.md).

1. "مشروع جديد": describe a simple app that manages one kind of record (tasks, products,
   appointments…), in Arabic or English, or pick an example.
2. Review the requirements. Use "طلب تعديل" to ask for a change, or approve.
3. Wait for the five agents. Then open the preview, the test report, the plan, and
   download the ZIP (open `index.html` from it on your computer).
4. Limits: a few projects per person per day. Please do not enter personal data.

With `BUNYAN_AUTH=required`, testers sign in with the user name and password they were given.
