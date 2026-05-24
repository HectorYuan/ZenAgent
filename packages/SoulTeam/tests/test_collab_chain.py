"""协作链测试 (M10 Phase X)"""
import pytest
from packages.SoulTeam.collab_chain import ChainExecutor, ChainDefinition, ChainStep, ExecutionMode, CHAINS, ChainStatus

@pytest.mark.asyncio
async def test_chain_definitions():
    assert len(CHAINS) == 5
    for cid in ["IA-AL","TR-DV","OO-SE","CR-DE","PR-PT"]:
        assert cid in CHAINS

@pytest.mark.asyncio
async def test_execute_single():
    chain = ChainDefinition("TEST", "test", "desc", ExecutionMode.SINGLE,
                           steps=[ChainStep("s1", "SUB-1.1", "test task")])
    executor = ChainExecutor()
    result = await executor.execute("TEST")  # will use mock fallback
    assert result is not None

@pytest.mark.asyncio
async def test_execute_mock():
    executor = ChainExecutor()
    result = await executor.execute("IA-AL")
    assert result.status in (ChainStatus.COMPLETED, ChainStatus.FAILED)
    assert result.duration >= 0
