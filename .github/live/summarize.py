"""Summary of one live journey: the journey result plus the real token usage and cost.

Reads the backend log ("BA model call:" lines written by the Business Analyst's direct
backend) and journey.json. Writes usage.json and summary.md into the output folder.

    python .github/live/summarize.py backend.log live-journey
"""

import json
import re
import sys
from pathlib import Path

PRICES = {"claude-opus-5-5": (4.00, 20.00)}  # USD per million input / output tokens
CALL = re.compile(r"BA model call: model=(\S+) input_tokens=(\d+) output_tokens=(\d+) stop_reason=(\S+) request_id=(\S+)")

log, out = Path(sys.argv[1]), Path(sys.argv[2])
calls = [dict(zip(("model", "input_tokens", "output_tokens", "stop_reason", "request_id"), m.groups()))
         for m in CALL.finditer(log.read_text(encoding="utf-8", errors="replace") if log.exists() else "")]
cost = 0.0
for c in calls:
    c["input_tokens"], c["output_tokens"] = int(c["input_tokens"]), int(c["output_tokens"])
    price_in, price_out = PRICES.get(c["model"], (None, None))
    c["cost_usd"] = round(c["input_tokens"] * price_in / 1e6 + c["output_tokens"] * price_out / 1e6, 4) if price_in else None
    cost += c["cost_usd"] or 0
usage = {"paid_requests": len(calls), "calls": calls, "estimated_cost_usd": round(cost, 4)}
(out / "usage.json").write_text(json.dumps(usage, indent=2), encoding="utf-8")

j = json.loads((out / "journey.json").read_text(encoding="utf-8")) if (out / "journey.json").exists() else {}
lines = ["# BUNYAN live journey (real Business Analyst LLM)", "",
         f"- Result: **{j.get('result', 'not run')}** in {j.get('duration_seconds')} s",
         f"- Paid model requests: {len(calls)}; estimated cost ${usage['estimated_cost_usd']} USD",
         f"- Project: `{j.get('project_id')}`"]
for c in calls:
    lines.append(f"  - {c['model']}: {c['input_tokens']} in / {c['output_tokens']} out, stop `{c['stop_reason']}`, ${c['cost_usd']}")
if j.get("error"):
    lines.append(f"- Stopped: {j['error']}")
if j.get("revision_notice"):
    lines.append(f"- Revision notice (`{j['revision_notice']['testid']}`): {j['revision_notice']['text']}")
if j.get("final"):
    lines.append(f"- Final: `{j['final']['status']}`, QA `{(j['final'].get('qa') or {}).get('status')}`, metrics {j['final'].get('metrics')}")
lines += ["", "| Step | s | Detail |", "|---|---|---|"]
lines += [f"| {s['name']} | {s['at_seconds']} | {json.dumps({k: v for k, v in s.items() if k not in ('name', 'at_seconds')}, ensure_ascii=False)} |"
          for s in j.get("steps", [])]
lines += ["", "| Check | Result |", "|---|---|"] + [f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in j.get("checks", {}).items()]
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
