from __future__ import annotations
from ngk_framework.base import Workspace
class WorktreeManager:
    def __init__(self, ws: Workspace): self.ws=ws
    def list(self): return {"status":"ok","worktrees":[],"write_agents_enabled":False}
