from __future__ import annotations
from dataclasses import dataclass
@dataclass
class Lock:
    path:str; task_id:str; mode:str='write'
class LockTable:
    def __init__(self): self.locks=[]
    def acquire(self, lock:Lock):
        for old in self.locks:
            if old.path == lock.path and (old.mode == 'write' or lock.mode == 'write'):
                return False
        self.locks.append(lock); return True
    def list(self): return [l.__dict__ for l in self.locks]
