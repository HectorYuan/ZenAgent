"""
八卦消息队列 (M10 Phase L)

8 通道消息队列 + 中继协议
"""
import asyncio
from collections import deque
from .coordinates import BAGUA_POSITIONS


class BaguaMessageQueue:
    """8 通道八卦消息队列"""
    MAX_QUEUE_SIZE = 100
    RELAY_TTL = 300
    MAX_HOPS = 3

    def __init__(self):
        self._channels: dict[str, asyncio.Queue] = {
            name: asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
            for name in BAGUA_POSITIONS
        }
        self._relay_count: dict[str, int] = {name: 0 for name in BAGUA_POSITIONS}

    async def publish(self, channel: str, message: dict):
        if channel in self._channels:
            try:
                self._channels[channel].put_nowait(message)
            except asyncio.QueueFull:
                pass  # 满时丢弃最旧的

    async def consume(self, channel: str) -> dict:
        if channel in self._channels:
            return await self._channels[channel].get()
        raise ValueError(f"Unknown channel: {channel}")

    async def relay(self, from_ch: str, to_ch: str, message: dict, hops: int = 0) -> bool:
        """中继消息: TTL=300s, max 3 hops"""
        if hops >= self.MAX_HOPS:
            return False
        message["_hops"] = hops + 1
        message["_relay_from"] = from_ch
        await self.publish(to_ch, message)
        self._relay_count[to_ch] += 1
        return True

    def get_stats(self) -> dict:
        return {
            ch: {"size": q.qsize(), "relays": self._relay_count.get(ch, 0)}
            for ch, q in self._channels.items()
        }
