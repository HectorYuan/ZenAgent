"""
ZenAgent 集成测试包

提供层间集成测试、Agent创建流程测试、协作流程测试和进化流程测试
"""

from .test_layer_integration import TestLayerIntegration, TestCrossLayerCallbacks, TestLayerDataFlow
from .test_agent_creation import TestAgentCreationFlow, TestAgentCreationValidation, AgentCreationFlow
from .test_collaboration import TestCollaborationFlow, TestMultiAgentCollaboration, TestCollaborationEdgeCases, CollaborationFlow
from .test_evolution import TestEvolutionFlow, TestEvolutionStages, TestEvolutionMetrics, TestEvolutionEdgeCases, EvolutionFlow
from .test_integration_simple import (
    TestSwarmFlyCore,
    TestCollaborationCore,
    TestSharedMemory,
    TestAgentStateMachine,
    TestTaskPriorities,
    TestMemorySegments,
    TestSwarmFlyComponents,
    TestIntegrationScenarios,
    TestErrorHandling,
    TestMultiAgentScenario,
)

__all__ = [
    # 层间集成测试
    "TestLayerIntegration",
    "TestCrossLayerCallbacks",
    "TestLayerDataFlow",
    
    # Agent 创建流程测试
    "TestAgentCreationFlow",
    "TestAgentCreationValidation",
    "AgentCreationFlow",
    
    # 协作流程测试
    "TestCollaborationFlow",
    "TestMultiAgentCollaboration",
    "TestCollaborationEdgeCases",
    "CollaborationFlow",
    
    # 进化流程测试
    "TestEvolutionFlow",
    "TestEvolutionStages",
    "TestEvolutionMetrics",
    "TestEvolutionEdgeCases",
    "EvolutionFlow",
    
    # 简化集成测试
    "TestSwarmFlyCore",
    "TestCollaborationCore",
    "TestSharedMemory",
    "TestAgentStateMachine",
    "TestTaskPriorities",
    "TestMemorySegments",
    "TestSwarmFlyComponents",
    "TestIntegrationScenarios",
    "TestErrorHandling",
    "TestMultiAgentScenario",
]
