# SoulTeam 模块

> 路径: `packages/SoulTeam/`

## 模块列表

### `core`

SoulTeam 层入口

MetaSoul 记忆系统和 SelfLearning 自学习系统的统一入口

**类:** `SoulTeamConfig`, `SoulTeam`

**函数:** `__init__`, `_init_memory`, `_init_learning`, `_init_reflection`, `_init_personality`, `store_memory`, `retrieve_memory`, `learn`, `process_feedback`, `reflect` ... (+6 more)

---

### `learning.feedback_processor`

反馈处理器

内部反馈和外部反馈的处理

**类:** `FeedbackSource`, `FeedbackType`, `Feedback`, `ProcessedFeedback`, `FeedbackProcessor`

**函数:** `__init__`, `process`, `_process_feedback`, `_evaluate_applicability`, `_adjust_weight`, `_calculate_impact`, `_generate_insights`, `_suggest_actions`, `_apply_to_learner`, `create_internal_feedback` ... (+4 more)

---

### `learning.knowledge_graph`

知识图谱

实体、关系和推理的实现

**类:** `EntityType`, `RelationType`, `Entity`, `Relation`, `KnowledgeQuery`, `KnowledgeGraph`

**函数:** `__init__`, `add_entity`, `update_entity`, `add_relation`, `get_entity`, `get_entity_by_name`, `get_entities_by_type`, `get_relations_from`, `get_relations_to`, `query` ... (+6 more)

---

### `learning.learner`

学习器核心

观察、反思、归纳、验证循环的实现

**类:** `LearningCycle`, `LearningResult`, `Observation`, `Reflection`, `Generalization`, `SelfLearner`

**函数:** `__init__`, `learn`, `_observe`, `_reflect`, `_generalize`, `_verify`, `_integrate`, `_process_feedback`, `_identify_patterns`, `_generate_hypotheses` ... (+7 more)

---

### `learning.learning_optimizer`

学习优化器

课程学习、迁移学习的实现

**类:** `CurriculumStage`, `TransferLearningResult`, `CurriculumItem`, `LearningOptimizer`

**函数:** `__init__`, `create_curriculum`, `add_curriculum_item`, `get_next_learning_item`, `update_progress`, `get_curriculum_progress`, `analyze_transferability`, `transfer_learning`, `learn_in_domain`, `get_domain_mastery` ... (+2 more)

---

### `learning.skill_acquisition`

技能获取

模仿学习、强化学习和知识蒸馏的实现

**类:** `SkillLevel`, `SkillRecord`, `Demonstration`, `LearningAttempt`, `SkillAcquisition`

**函数:** `add_experience`, `_update_level`, `practice`, `__init__`, `learn_from_demonstration`, `_extract_from_demonstration`, `provide_demonstration`, `reinforce_learning`, `apply_skill`, `distill_knowledge` ... (+8 more)

---

### `memory.forgetting`

遗忘机制

自然遗忘和重要记忆保留的实现

**类:** `ForgettingPolicy`, `ForgettingCurve`, `MemoryConsolidation`, `ForgettingMechanism`

**函数:** `calculate_retention`, `__init__`, `protect_memory`, `unprotect_memory`, `is_protected`, `calculate_decay`, `should_forget`, `run_forgetting_cycle`, `consolidate_memories`, `get_consolidation` ... (+2 more)

---

### `memory.memory_hierarchy`

记忆层次结构

工作记忆、情景记忆、语义记忆、程序记忆的实现

**类:** `MemoryTier`, `WorkingMemoryEntry`, `EpisodicMemoryEntry`, `SemanticMemoryEntry`, `ProceduralMemoryEntry`, `WorkingMemory`, `EpisodicMemory`, `SemanticMemory`, `ProceduralMemory`, `MemoryHierarchy`

**函数:** `is_expired`, `access`, `__init__`, `store`, `retrieve`, `update_attention`, `set_attention_focus`, `clear`, `_evict_lowest_attention`, `get_all` ... (+21 more)

---

### `memory.memory_index`

记忆索引

向量索引和语义检索的实现

**类:** `SemanticSearchResult`, `IndexEntry`, `InvertedIndex`, `VectorIndex`, `MemoryIndex`

**函数:** `__init__`, `add`, `remove`, `search`, `_extract_keywords`, `__init__`, `add`, `remove`, `search`, `_cosine_distance` ... (+9 more)

---

### `memory.memory_store`

记忆存储

可插拔后端的记忆存储实现

**类:** `MemoryStorageBackend`, `MemoryStoreConfig`, `InMemoryStorageBackend`, `FileStorageBackend`, `MemoryStore`

**函数:** `save`, `load`, `delete`, `query`, `exists`, `__init__`, `save`, `load`, `delete`, `query` ... (+25 more)

---

### `memory.meta_soul`

MetaSoul 核心类

灵魂记忆、经验积累和人格演化的核心实现

**类:** `MemoryType`, `MemoryImportance`, `MemoryEntry`, `SoulExperience`, `SoulMemory`, `MetaSoul`

**函数:** `access`, `add_association`, `get_decay_score`, `to_dict`, `add_memory`, `add_experience`, `get_memories_by_type`, `get_recent_memories`, `__init__`, `store_memory` ... (+11 more)

---

### `personality.belief_system`

信念系统

管理和演化信念的核心实现

**类:** `BeliefStrength`, `Belief`, `BeliefSystem`

**函数:** `strengthen`, `weaken`, `__init__`, `create_belief`, `_index_belief`, `get_belief`, `update_belief`, `reinforce_belief`, `challenge_belief`, `create_contradiction` ... (+7 more)

---

### `personality.personality`

人格模型

Big Five 人格维度的实现

**类:** `BigFiveTraits`, `PersonalityState`, `TraitProfile`, `Personality`

**函数:** `__init__`, `_init_trait_profile`, `get_trait`, `get_traits`, `set_trait`, `_update_trait_profile`, `evolve`, `_adjust_trait`, `_record_evolution`, `adjust_stability` ... (+5 more)

---

### `personality.trait_dynamics`

特质动态变化

人格特质随时间和经验的变化

**类:** `EnvironmentalFactor`, `TraitChange`, `TraitDynamicsConfig`, `TraitDynamics`

**函数:** `__init__`, `process_experience`, `_calculate_delta`, `_apply_change`, `_update_environmental_factors`, `get_recent_changes`, `get_change_trend`, `get_environmental_factors`, `on_trait_change`

---

### `personality.value_evolution`

价值观演化

价值观的优先级和演化

**类:** `ValuePriority`, `Value`, `ValueEvolution`

**函数:** `update_priority`, `align_with_action`, `__init__`, `create_value`, `get_value`, `get_value_by_name`, `set_as_core`, `update_value_from_experience`, `_record_evolution`, `align_behavior` ... (+5 more)

---

### `reflection.experience_analyzer`

经验分析器

深入分析经验模式和趋势

**类:** `ExperiencePattern`, `TrendAnalysis`, `PatternMatch`, `ExperienceAnalyzer`

**函数:** `__init__`, `analyze`, `_analyze_outcome`, `_analyze_sentiment`, `_identify_patterns`, `_analyze_associations`, `_assess_value`, `analyze_trends`, `find_similar_experiences`, `generate_insights_report`

---

### `reflection.insight_extractor`

洞察提取器

从经验中提取深层次洞察

**类:** `InsightType`, `Insight`, `InsightExtractor`

**函数:** `get_score`, `__init__`, `extract`, `_extract_causal_insights`, `_extract_correlational_insights`, `_extract_temporal_insights`, `_extract_procedural_insights`, `_find_common_factors`, `_extract_elements`, `_store_insight` ... (+4 more)

---

### `reflection.pattern_recognizer`

模式识别器

识别和跟踪行为与经验模式

**类:** `PatternType`, `Pattern`, `PatternRecognizer`

**函数:** `__init__`, `register_event`, `_detect_sequential_pattern`, `_detect_cyclic_pattern`, `_detect_habit_pattern`, `detect_anomalies`, `get_pattern`, `get_patterns_by_type`, `get_active_patterns`, `update_pattern_strength` ... (+3 more)

---

### `reflection.reflector`

反思引擎

反思和经验分析的核心实现

**类:** `ReflectionDepth`, `ReflectionResult`, `Reflector`

**函数:** `__init__`, `reflect`, `_perform_reflection`, `_summarize_experience`, `_analyze_causes`, `_analyze_effects`, `_extract_meaning`, `_extract_lessons`, `_generate_actions`, `_integrate_reflection` ... (+3 more)

---

### `tests.test_learning`

Learning 模块测试

**类:** `TestSelfLearner`, `TestFeedbackProcessor`, `TestKnowledgeGraph`, `TestSkillAcquisition`, `TestLearningOptimizer`

**函数:** `setUp`, `test_learn`, `test_learning_cycle`, `test_stats`, `setUp`, `test_process_feedback`, `test_create_internal_feedback`, `test_feedback_stats`, `setUp`, `test_add_entity` ... (+15 more)

---

### `tests.test_memory`

Memory 模块测试

**类:** `TestMetaSoul`, `TestMemoryHierarchy`, `TestMemoryStore`, `TestMemoryIndex`, `TestForgettingMechanism`

**函数:** `setUp`, `test_store_memory`, `test_retrieve_memory`, `test_store_experience`, `test_associate_memories`, `test_get_stats`, `setUp`, `test_working_memory`, `test_store_and_retrieve`, `setUp` ... (+9 more)

---

### `tests.test_personality`

Personality 模块测试

**类:** `TestPersonality`, `TestTraitDynamics`, `TestBeliefSystem`, `TestValueEvolution`

**函数:** `setUp`, `test_initial_traits`, `test_get_trait`, `test_set_trait`, `test_evolve`, `test_predict_behavior`, `test_reset`, `setUp`, `test_process_experience`, `test_get_recent_changes` ... (+20 more)

---

### `tests.test_reflection`

Reflection 模块测试

**类:** `TestReflector`, `TestExperienceAnalyzer`, `TestInsightExtractor`, `TestPatternRecognizer`

**函数:** `setUp`, `test_reflect_surface`, `test_reflect_causal`, `test_reflect_deep`, `test_get_recent_reflections`, `setUp`, `test_analyze_outcome`, `test_analyze_negative_outcome`, `test_identify_patterns`, `test_analyze_trends` ... (+11 more)

---

### `tests.test_soulteam`

SoulTeam层测试

**类:** `TestSoulTeam`

**函数:** `test_metasoul_creation`, `test_learner_creation`, `test_reflector_creation`, `test_personality_creation`

---

