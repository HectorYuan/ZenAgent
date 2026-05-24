"""八卦拓扑管理 (M10 Phase K)"""
import time, asyncio
from .coordinates import BAGUA_POSITIONS
class TopologyManager:
    def __init__(self):
        self._nodes = {n: {"status":"online","load":0,"updated":time.time()} for n in BAGUA_POSITIONS}
        self._lock = asyncio.Lock()
    async def mark_offline(self, n: str):
        async with self._lock:
            if n in self._nodes: self._nodes[n]["status"]="offline"
    async def get_online(self) -> list[str]:
        async with self._lock:
            return [n for n,d in self._nodes.items() if d["status"]=="online"]
    def get_topology(self) -> dict: return dict(self._nodes)
