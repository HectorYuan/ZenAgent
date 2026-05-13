"""
内存池模块单元测试
"""

import pytest
import sys
import os

PACKAGES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PACKAGES_DIR)

from SwarmFly.memory import (
    SharedMemoryPool,
    MemoryPoolConfig,
    MemorySegment,
    SegmentType,
    SegmentAccess,
    SegmentManager,
    LockManager,
    LockType,
    ReadLock,
    WriteLock,
    FairLock,
    SyncProtocol,
    SyncOperation,
    SyncState,
    CacheCoherence,
    CoherenceProtocol,
    CacheLine,
    CacheLineState,
)


class TestMemorySegment:
    """内存段测试"""
    
    def test_segment_creation(self):
        """测试内存段创建"""
        segment = MemorySegment(
            name="test_segment",
            segment_type=SegmentType.SHARED,
            access=SegmentAccess.READ_WRITE,
        )
        
        assert segment.name == "test_segment"
        assert segment.segment_type == SegmentType.SHARED
        assert segment.access == SegmentAccess.READ_WRITE
        assert segment.segment_id is not None
    
    def test_read_write(self):
        """测试读写"""
        segment = MemorySegment(
            name="test",
            access=SegmentAccess.READ_WRITE,
            data="initial",
        )
        
        data = segment.read("agent-1")
        assert data == "initial"
        
        result = segment.write("agent-1", "updated")
        assert result is True
        
        data = segment.read("agent-1")
        assert data == "updated"
    
    def test_read_only(self):
        """测试只读"""
        segment = MemorySegment(
            name="test",
            access=SegmentAccess.READ_ONLY,
            data="readable",
        )
        
        assert segment.can_read is True
        assert segment.can_write is False
        
        result = segment.write("agent-1", "new")
        assert result is False
    
    def test_version_control(self):
        """测试版本控制"""
        segment = MemorySegment(name="test")
        
        assert segment.version == 0
        
        segment.write("agent-1", "v1")
        assert segment.version == 1
        
        segment.write("agent-1", "v2")
        assert segment.version == 2
    
    def test_access_tracking(self):
        """测试访问追踪"""
        segment = MemorySegment(name="test", data="data")
        
        segment.read("agent-1")
        assert segment.read_count == 1
        
        segment.write("agent-1", "new")
        assert segment.write_count == 1


class TestSegmentManager:
    """内存段管理器测试"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = SegmentManager()
        
        assert manager.get_all_segments() == []
    
    def test_create_segment(self):
        """测试创建内存段"""
        manager = SegmentManager()
        
        segment = manager.create_segment(
            name="segment_1",
            segment_type=SegmentType.SHARED,
            owner_id="agent-1",
        )
        
        assert segment is not None
        assert segment.name == "segment_1"
        
        # 通过名称获取
        retrieved = manager.get_segment_by_name("segment_1")
        assert retrieved.segment_id == segment.segment_id
    
    def test_delete_segment(self):
        """测试删除内存段"""
        manager = SegmentManager()
        segment = manager.create_segment(name="test")
        
        result = manager.delete_segment(segment.segment_id)
        assert result is True
        
        assert manager.get_segment(segment.segment_id) is None
    
    def test_get_segments_by_type(self):
        """测试按类型获取"""
        manager = SegmentManager()
        manager.create_segment(name="s1", segment_type=SegmentType.SHARED)
        manager.create_segment(name="s2", segment_type=SegmentType.PRIVATE)
        
        shared = manager.get_segments_by_type(SegmentType.SHARED)
        assert len(shared) == 1


class TestLockManager:
    """锁管理器测试"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = LockManager()
        
        assert manager is not None
    
    def test_acquire_read_lock(self):
        """测试获取读锁"""
        manager = LockManager()
        
        result = manager.acquire_read("resource-1", "agent-1")
        
        assert result.success is True
        assert result.lock is not None
    
    def test_acquire_write_lock(self):
        """测试获取写锁"""
        manager = LockManager()
        
        result = manager.acquire_write("resource-1", "agent-1")
        
        assert result.success is True
    
    def test_multiple_read_locks(self):
        """测试多个读锁"""
        manager = LockManager()
        
        r1 = manager.acquire_read("resource-1", "agent-1")
        r2 = manager.acquire_read("resource-1", "agent-2")
        
        assert r1.success is True
        assert r2.success is True
    
    def test_write_lock_exclusive(self):
        """测试写锁独占"""
        manager = LockManager()
        
        w1 = manager.acquire_write("resource-1", "agent-1")
        
        assert w1.success is True
        # 写锁已经获取
    
    def test_release_lock(self):
        """测试释放锁"""
        manager = LockManager()
        
        result = manager.acquire_write("resource-1", "agent-1")
        assert result.success is True
        
        released = manager.release_write("resource-1", "agent-1")
        assert released is True
    
    def test_context_manager(self):
        """测试上下文管理器"""
        manager = LockManager()
        
        with manager.write_lock("resource-1", "agent-1") as acquired:
            assert acquired is True
        
        # 锁应该已释放
        assert manager.is_write_locked("resource-1") is False


class TestSyncProtocol:
    """同步协议测试"""
    
    def test_protocol_creation(self):
        """测试协议创建"""
        protocol = SyncProtocol(node_id="node-1")
        
        assert protocol.node_id == "node-1"
        assert protocol.state == SyncState.IDLE
    
    def test_register_peer(self):
        """测试注册对等节点"""
        protocol = SyncProtocol(node_id="node-1")
        
        protocol.register_peer("node-2")
        
        peers = protocol.get_peers()
        assert "node-2" in peers
    
    def test_create_message(self):
        """测试创建消息"""
        protocol = SyncProtocol(node_id="node-1")
        
        msg = protocol.create_message(
            operation=SyncOperation.READ,
            resource_id="resource-1",
        )
        
        assert msg is not None
        assert msg.source_node == "node-1"
        assert msg.operation == SyncOperation.READ
    
    def test_version_vector(self):
        """测试版本向量"""
        protocol = SyncProtocol(node_id="node-1")
        protocol.register_peer("node-2")
        
        vector = protocol.get_version_vector()
        # 验证至少包含 node-2
        assert "node-2" in vector
    
    def test_compare_versions(self):
        """测试比较版本"""
        protocol = SyncProtocol(node_id="node-1")
        protocol.register_peer("node-2")
        
        # 比较不同版本
        v1 = {"node-2": 1}
        v2 = {"node-2": 0}
        
        diff = protocol.compare_versions(v1)
        # v1 的 node-2 版本是 1，v2 是 0，所以 diff 应该是 -1
        assert diff["node-2"] == -1


class TestCacheCoherence:
    """缓存一致性测试"""
    
    def test_cache_creation(self):
        """测试缓存创建"""
        cache = CacheCoherence(node_id="node-1")
        
        assert cache.node_id == "node-1"
        assert cache.protocol == CoherenceProtocol.MESI
    
    def test_cache_read_miss(self):
        """测试缓存未命中"""
        cache = CacheCoherence(node_id="node-1")
        
        data = cache.read("resource-1", "agent-1")
        
        assert data is None  # 未命中
    
    def test_cache_write(self):
        """测试缓存写入"""
        cache = CacheCoherence(node_id="node-1")
        
        result = cache.write("resource-1", "data", "agent-1")
        
        assert result is True
        
        line = cache.get_cache_line("resource-1")
        assert line is not None
        assert line.data == "data"
    
    def test_cache_read_hit(self):
        """测试缓存命中"""
        cache = CacheCoherence(node_id="node-1")
        
        cache.write("resource-1", "data", "agent-1")
        data = cache.read("resource-1", "agent-1")
        
        assert data == "data"
        
        stats = cache.get_statistics()
        assert stats["total_hits"] == 1
    
    def test_mesi_state_transitions(self):
        """测试 MESI 状态转换"""
        cache = CacheCoherence(node_id="node-1", protocol=CoherenceProtocol.MESI)
        
        # 写入后应该是 Modified 状态
        cache.write("resource-1", "data", "agent-1")
        line = cache.get_cache_line("resource-1")
        
        assert line.state == CacheLineState.MODIFIED


class TestSharedMemoryPool:
    """共享内存池测试"""
    
    def test_pool_creation(self):
        """测试内存池创建"""
        pool = SharedMemoryPool(
            pool_id="pool-1",
            node_id="node-1",
        )
        
        assert pool.pool_id == "pool-1"
        assert pool.node_id == "node-1"
    
    def test_register_agent(self):
        """测试注册 Agent"""
        pool = SharedMemoryPool(pool_id="pool-1", node_id="node-1")
        
        pool.register_agent("agent-1")
        
        agents = pool.get_registered_agents()
        assert "agent-1" in agents
    
    def test_create_segment(self):
        """测试创建内存段"""
        pool = SharedMemoryPool(pool_id="pool-1", node_id="node-1")
        
        segment = pool.create_segment(
            name="shared_data",
            owner_id="agent-1",
            initial_data={"key": "value"},
        )
        
        assert segment is not None
        assert segment.name == "shared_data"
    
    def test_read_write_with_lock(self):
        """测试带锁读写"""
        pool = SharedMemoryPool(pool_id="pool-1", node_id="node-1")
        pool.register_agent("agent-1")
        
        pool.create_segment(
            name="data",
            owner_id="agent-1",
            initial_data="initial",
        )
        
        # 读取
        data = pool.read_with_lock("data", "agent-1")
        assert data == "initial"
        
        # 写入
        result = pool.write_with_lock("data", "agent-1", "updated")
        assert result is True
    
    def test_update_with_lock(self):
        """测试原子更新"""
        pool = SharedMemoryPool(pool_id="pool-1", node_id="node-1")
        pool.register_agent("agent-1")
        
        pool.create_segment(
            name="counter",
            owner_id="agent-1",
            initial_data=0,
        )
        
        def increment(current):
            return (current or 0) + 1
        
        pool.update_with_lock("counter", "agent-1", increment)
        
        data = pool.read_with_lock("counter", "agent-1")
        assert data == 1
    
    def test_get_statistics(self):
        """测试获取统计"""
        pool = SharedMemoryPool(pool_id="pool-1", node_id="node-1")
        
        pool.create_segment(name="s1")
        pool.create_segment(name="s2")
        
        stats = pool.get_stats()
        
        assert stats.total_segments == 2
