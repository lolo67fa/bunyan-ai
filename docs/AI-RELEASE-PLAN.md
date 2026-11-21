# Secure AI Capabilities: Settings and Staged Release

This covers the protected real Business Analyst (`BUNYAN_LLM_ACCESS=codes`, since PR #17) and the
AI repair strategy (`BUNYAN_REPAIR=llm`, PR `feature/secure-ai-capabilities`). **Both are off in
production** until the project lead approves the settings below, stage by stage.

## 1. Proposed settings (awaiting approval)

| Setting | Proposed value | Why |
|---|---|---|
| Model | `claude-opus-5-5` | Used for every verified real run so far. $4 / $20 per million input / output tokens (Anthropic first-party price, checked 2026-11-21). |
| Real analysis: worst case | **$0.72** per request (20,000 input + 32,000 output tokens) | Reserved before each request. |
| Real analysis: measured | **$0.23–0.27** per request (runs 42211456095, 44716341099, 44769184001) | Booked from the API's reported usage. |
| AI repair: worst case | **$0.28** per request (30,000 input + 8,000 output tokens) | Reserved before each request. |
| AI repair: expected | about $0.05 (≈9,000 input + 700 output tokens) | From an offline run; **not yet measured with a real paid call**. |
| Analyses per access code per day | 3 (`BUNYAN_LLM_MAX_PER_CODE_PER_DAY`) | Covers one idea, one clarification and one change request. |
| AI repairs per access code per day | 3 (`BUNYAN_LLM_REPAIRS_PER_CODE_PER_DAY`) | At most 2 are used per project. |
| Real analyses, whole site, per day | 10 (`BUNYAN_MAX_LLM_ANALYSES_PER_DAY`, today 0) | Hard cap, independent of the budget. |
| Concurrent paid requests | 1 (`BUNYAN_MAX_CONCURRENT_ANALYSES=1`) | One at a time. |
| Daily budget, whole site | **$3** (`BUNYAN_LLM_DAILY_BUDGET_USD`) | Never exceeded: each request's worst case is reserved under a lock before it is sent. |
| Monthly cap at Anthropic | $10–20 (set by the lead in the Anthropic Console) | Second, independent limit outside BUNYAN. |
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
| **B** | Real analyst for authorised testers: the variables in section 1, the API key set by the lead, codes issued | Approval of the model, limits and budget |
| **C** | One approved paid request on the live site (≈ $0.27), end to end to the ZIP | Approval of one paid call |
| **D** | `BUNYAN_REPAIR=llm` for the same testers | Separate security, budget and paid-test approval |
| **E** | Wider availability | Only after observing real reliability and cost |

## 6. Rollback

- **Instant, no redeploy of code:** remove `BUNYAN_LLM_ACCESS` (back to mock for everyone) and/or
  set `BUNYAN_REPAIR=restore` in Railway Variables. Railway restarts the service with the volume intact.
- **Code:** Railway → service `bunyan` → Deployments → redeploy the previous successful deployment
  (currently `d0ad75d8`, `main` @ `9d22bd8`).
- Projects, sessions, the volume and every other variable are not touched by either step.
