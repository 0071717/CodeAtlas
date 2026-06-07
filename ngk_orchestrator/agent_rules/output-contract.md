# Output Contract

Return exactly one machine-readable result block:

```text
<ngk_agent_result>
{ valid JSON matching schema_version 1 }
</ngk_agent_result>
```

The JSON must include status, verdict, confidence, summary, findings, uncertainties, not_confirmed, and requested_followups.

Each finding must include finding_id, severity, title, claim, support, confidence, fact_ids, evidence, recommended_tests, and risk_tags.
