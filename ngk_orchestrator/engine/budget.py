from dataclasses import dataclass
@dataclass
class OrchestrationBudget:
    max_parallel_agents:int=2
    max_context_facts:int=30
