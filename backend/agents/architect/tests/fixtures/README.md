Copied unchanged from `backend/agents/business_analyst/samples/outputs/` on `main`
(including PR #8, requirements contract `0.1.0-proposal`), so the Architect tests run
on exactly the samples the Business Analyst ships. Refresh them whenever the requirements
contract or its samples change:

```bash
cp backend/agents/business_analyst/samples/outputs/*.requirements.json backend/agents/architect/tests/fixtures/
```

`real_llm_inventory_ar.requirements.json` is different: the unedited output of one real
`claude-opus-5-5` Business Analyst run (GitHub Actions run 44716341099). It keeps the
regression tests honest about how the model really words validation criteria.
