# Secure AI Capabilities: Settings and Staged Release

This covers the protected real Business Analyst (`BUNYAN_LLM_ACCESS=codes`, since PR #17) and the
AI repair strategy (`BUNYAN_REPAIR=llm`, PR `feature/secure-ai-capabilities`). **Both are off in
production** until the project lead approves the settings below, stage by stage.

## 0. The $5 cumulative experiment budget

`BUNYAN_TOTAL_LLM_BUDGET_USD=5.00` is the **total** for the whole experiment, across analyses and AI
repairs, all access codes and all sessions. The ledger lives on the volume
(`/data/llm_budget.json` with the sentinel `/data/llm_budget.initialized`).
- **Never reset:** not at midnight, on restart or redeploy, for new guests, or when codes change.
- **Accounting:** integer micro-dollars.
- **Before each request:** the worst case is reserved on disk under a lock.
- **After each request:** the reservation is replaced by the real usage; unknown cost books the worst case.
- **After a crash or redeploy mid-request:** the left-over reservation is booked at its worst case.

**Fail closed.** Each of these blocks paid requests, and the guest site keeps working with the mock:
- the ledger is missing, corrupted or inconsistent;
- the sentinel is missing next to an existing ledger;
- the total in the variable differs from the ledger's total.

A deleted ledger is never recreated, because the sentinel remains.

**Creation.** The ledger is created once, on the first paid-path check after `BUNYAN_LLM_ACCESS=codes` is on, and only if `BUNYAN_LLM_BUDGET_STARTING_SPENT_USD` is set. It has no default: the starting balance is the lead's decision. With codes on but no total budget, the server refuses to start.

**Exhausted.** «انتهت الميزانية الإجمالية للتجربة؛ لا يمكن إجراء تحليل حقيقي آخر.» (429). No request is sent, and guests keep the mock analyst.

**Admin summary:** `GET /admin/llm-budget` with the HTTP Basic login of a user in `BUNYAN_ADMINS` (the user must be in `BUNYAN_USERS`). It shows total, starting balance, spent, reserved, remaining, per-code counts and recent amounts, by code label only.

### Historical paid spend (before the ledger)

| GitHub Actions run | Date | Requests | Cost (list price, from logged usage) |
|---|---|---|---|
| 42211109903 | Nov 6 | 0 (refused by the confirmation guard) | $0.0000 |
| 42211456095 | Nov 6 | 1 | $0.2692 |
| 44716341099 | Nov 20 | 1 | $0.2277 |
| 44725920842 | Nov 20 | 2 (analysis + one revision) | $0.5218 |
| 44769184001 | Nov 20 | 1 | $0.2732 |
| **Total** | | **5** | **$1.2919** |

Uncertain:
- These are list-price estimates from the logged token usage, not invoices.
- Free pre-flight calls (model lookup, token counting) are not included.
- Any other use of the same API key outside BUNYAN is unknown to the app.

**Decision needed:** start the ledger at `1.2919` (remaining $3.7081) or at `0` (the experiment counts only new requests).

### Provider-side cap (Anthropic Console)

Anthropic documents a **monthly** spend limit for the organization and for each workspace (Console → Settings → Spend limits; docs: `platform.claude.com/docs/en/api/rate-limits.md`, "Setting your own spend limit", and `.../manage-claude/workspaces.md`, "Setting workspace limits").

- The limit resets at 00:00 UTC on the 1st of each month. It is **not** a lifetime cap.
- When it is reached, requests are refused.
- The docs do not say whether usage can overshoot before enforcement.
- The docs do not describe prepaid credits or auto-reload.
- A limit on the Default Workspace "might not count or stop some usage".

**Recommended (the lead sets it; nothing here changes billing):**
1. Create a dedicated workspace, for example `bunyan-experiment`.
2. Create a new API key in it, used only by Railway.
3. Set the workspace's monthly limit to $5.
4. After the experiment, revoke that key.

Together with the app's cumulative ledger, that gives two independent limits. Neither can guarantee an exact maximum on the invoice. Other keys, other workspaces and any reporting delay are outside the app's control.

## 1. Proposed settings (awaiting approval)

| Setting | Proposed value | Why |
|---|---|---|
| Model | `claude-opus-5-5` | Used for every verified real run so far. $4 / $20 per million input / output tokens (Anthropic first-party price, checked 2026-11-21). |
| Real analysis: worst case | **$0.72** per request (20,000 input + 32,000 output tokens) | Reserved before each request. |
| Real analysis: measured | **$0.23–0.27** per request (runs 42211456095, 44716341099, 44769184001) | Booked from the API's reported usage. |
| AI repair: worst case | **$0.28** per request (30,000 input + 8,000 output tokens) | Reserved before each request. |
| AI repair: expected | about $0.05 (≈9,000 input + 700 output tokens) | From an offline run; **not yet measured with a real paid call**. |
| Testers | **one** access code at first | |
| Analyses per access code, whole experiment | **2** (`BUNYAN_LLM_MAX_ANALYSES_PER_CODE_TOTAL=2`) | Stored in the ledger; never resets. |
| Analyses per access code per day | 2 (`BUNYAN_LLM_MAX_PER_CODE_PER_DAY`) | Extra safeguard. |
| AI repairs | **off** (`BUNYAN_REPAIR=restore`) | Stage D only. |
| Real analyses, whole site, per day | 10 (`BUNYAN_MAX_LLM_ANALYSES_PER_DAY`, today 0) | Hard cap, independent of the budget. |
| Concurrent paid requests | 1 analysis (`BUNYAN_MAX_CONCURRENT_ANALYSES=1`) and 1 AI repair (fixed lock) at a time | Bounded load and spend. |
| **Total budget, whole experiment** | **$5.00** (`BUNYAN_TOTAL_LLM_BUDGET_USD`), starting balance per the decision above | Never reset; reserved before each request. |
| Daily budget, whole site | $2 (`BUNYAN_LLM_DAILY_BUDGET_USD`) | Extra safeguard. |
| Monthly cap at Anthropic | $5 on a dedicated workspace and key (set by the lead) | Independent limit outside BUNYAN. |
| Grant lifetime | 12 h (`BUNYAN_LLM_ACCESS_HOURS`) | A code must be re-entered after that. |
| Wrong-code limit | 8 per address per 15 min | Fixed in code. |

Startup refuses to run with retries, SDK retries or fallbacks on, an output cap above 32,000, a
non-direct backend, a model without a known price, or a budget below one request's worst case.

## 2. Access codes

- **Issue:** run `python -m backend.security hash-password <label>` (for example `tester-sara`). It
  asks for the code and prints `label:pbkdf2:…`. Give the code to the tester privately. Put only the
  printed line in Railway's `BUNYAN_LLM_ACCESS_CODES` (comma separated). Codes never go to GitHub
  or chat.
- **Revoke:** remove that label's entry and redeploy. Existing grants for the label stop at once,
  because every request checks that the label is still configured.
- **Audit:** the server logs the label, the reservation, the booked cost and refusals. It never
  logs the code, the session or the address. Daily totals are in `/data/llm_access.json`.

## 3. Secret rotation

- **API key:** create a new key in the Anthropic Console, replace `ANTHROPIC_API_KEY` in Railway
  Variables, redeploy, then delete the old key in the Console.
- **Access codes:** issue new codes and replace `BUNYAN_LLM_ACCESS_CODES`.
- **Session secret:** rotating `BUNYAN_SESSION_SECRET` signs everyone out and makes old guest
  projects unreachable (they stay on disk), so rotate it only on suspicion.

## 4. Expected failure behaviour

| Situation | What the user sees | Cost |
|---|---|---|
| No code, or an expired code | The mock analyst, as today | none |
| Wrong code | «رمز الوصول غير صحيح.»; after 8 tries, wait 15 min | none |
| Per-code or site limit reached | «استُخدم هذا الرمز 3 مرات اليوم…» / «انتهت حصة التحليل…» (429) | none |
| Budget would be exceeded | «بلغت ميزانية التحليل الحقيقي لهذا اليوم حدها.» (429) | none |
| Model timeout or API error | A safe error; the analysis can be retried; the worst case is booked | ≤ worst case |
| Invalid model output | The analysis fails safely (no fallback to mock) | one request |
| AI repair not possible (no code, limit, budget) | Repair history: «لم يُطلب إصلاح بالذكاء الاصطناعي»; the real QA result stays | none |
| AI repair proposes an unsafe or invalid edit | «رُفض اقتراح الإصلاح ولم يُطبَّق»; nothing is written | one request |

## 5. Staged release

| Stage | What | Needs |
|---|---|---|
| **A** | Deploy this PR with `BUNYAN_LLM_ACCESS` unset and `BUNYAN_REPAIR` unset (= `restore`). Production behaves as today. | Merge and deploy approval |
| **B** | Real analyst for **one** tester: the variables in section 1, the starting balance, the API key set by the lead, one code issued | Approval of the model, limits, budget and starting balance |
| **C** | One approved paid request on the live site (≈ $0.27), end to end to the ZIP | Approval of one paid call |
| **D** | `BUNYAN_REPAIR=llm` for the same testers | Separate security, budget and paid-test approval |
| **E** | Wider availability | Only after observing real reliability and cost |

## 6. Rollback

- **Instant, no redeploy of code:** remove `BUNYAN_LLM_ACCESS` (back to mock for everyone) and/or
  set `BUNYAN_REPAIR=restore` in Railway Variables. Railway restarts the service with the volume intact.
- **Code:** Railway → service `bunyan` → Deployments → redeploy the previous successful deployment
  (currently `d0ad75d8`, `main` @ `9d22bd8`).
- Projects, sessions, the volume and every other variable are not touched by either step.
