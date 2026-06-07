from __future__ import annotations
from typing import Any


def classify(files: list[str]) -> set[str]:
    domains=set()
    for f in files:
        l=f.lower()
        if any(x in l for x in ['ui/','frontend','react','.tsx','.jsx','.ts']): domains.add('frontend')
        if any(x in l for x in ['api/','backend','fastapi','openapi','pydantic','route']): domains.add('api')
        if any(x in l for x in ['data','opensearch','schema','model']): domains.add('data')
        if any(x in l for x in ['auth','secret','password','token','.env']): domains.add('security')
        if 'test' in l or 'spec' in l: domains.add('tests')
    return domains

def plan_review(changed_files: list[str], *, agents_enabled: bool=False) -> list[dict[str, Any]]:
    domains=classify(changed_files)
    tasks=[{"profile":"impact-analyzer","depends_on":[],"reason":"always run deterministic impact analysis"}]
    if 'api' in domains: tasks.append({"profile":"api-contract-reviewer","depends_on":["impact-analyzer"],"reason":"API/backend change detected"})
    if 'frontend' in domains: tasks.append({"profile":"frontend-impact-reviewer","depends_on":["impact-analyzer"],"reason":"UI/frontend change detected"})
    if 'data' in domains: tasks.append({"profile":"data-impact-reviewer","depends_on":["impact-analyzer"],"reason":"data change detected"})
    if {'api','frontend'} <= domains or any('api_client' in f.lower() or 'openapi' in f.lower() for f in changed_files):
        tasks.append({"profile":"cross-stack-contract-reviewer","depends_on":["impact-analyzer"],"reason":"UI/API boundary impact detected"})
    tasks.append({"profile":"test-gap-reviewer","depends_on":["impact-analyzer"],"reason":"review test coverage gaps"})
    if 'security' in domains: tasks.append({"profile":"security-reviewer","depends_on":["impact-analyzer"],"reason":"security-sensitive change detected"})
    if agents_enabled:
        tasks.append({"profile":"critic","depends_on":[t['profile'] for t in tasks if t['profile']!='critic'],"reason":"mandatory critic for child-agent review"})
    tasks.append({"profile":"synthesis","depends_on":[t['profile'] for t in tasks],"reason":"synthesize audited findings"})
    return tasks
