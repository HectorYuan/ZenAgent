# M8 P4: 人格动态权重矩阵 设计方案

**日期**: 2026-05-21
**版本**: v1.0（三专家评审优化已整合）
**设计依据**: [E2E_OPTIMIZATION_DESIGN §模块10](../E2E_OPTIMIZATION_DESIGN.md)

---

## 一、方案定位

升级现有 `Personality`（Big Five 基线值 + 线性调整）和 `ZenAgent._apply_personality_to_messages()`（生硬参数文本注入）为**5×8 场景矩阵 + EMA 平滑 + 自然语言画像注入 + 交叉效应 + 一致性校验**。

## 二、架构图

```
                    ┌──────────────────────────┐
                    │     ZenAgent.think()      │
                    └──────────┬───────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
    │DynamicAdjuster│  │Personality   │  │ConsistencyChecker │
    │场景检测+调整  │  │Matrix        │  │响应校验           │
    │on_new_turn() │  │5×8 矩阵     │  │overall_score()    │
    └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
           │                 │                    │
           └────────┬────────┘                    │
                    ▼                             │
           ┌──────────────┐                       │
           │Personality   │                       │
           │Injector      │                       │
           │to_narrative()│                       │
           │交叉效应模板  │                       │
           └──────┬───────┘                       │
                  ▼                               ▼
           ┌──────────────────────────────────────────┐
           │       注入到 LLM Messages                 │
           └──────────────────────────────────────────┘
```

## 三、核心组件

### 3.1 PersonalityMatrix — 5×8 权重矩阵

| 场景 \ 维度 | O | C | E | A | N |
|------------|---|---|---|---|---|
| casual_chat | 0.6 | 0.3 | 0.7 | 0.7 | 0.3 |
| technical_qa | 0.5 | 0.9 | 0.3 | 0.4 | 0.2 |
| creative | 1.0 | 0.3 | 0.6 | 0.5 | 0.4 |
| decision | 0.4 | 0.9 | 0.3 | 0.3 | 0.2 |
| debate | 0.7 | 0.6 | 0.6 | 0.2 | 0.3 |
| teaching | 0.6 | 0.7 | 0.5 | 0.8 | 0.2 |
| emotional_support | 0.4 | 0.4 | 0.5 | 0.95 | 0.3 |
| code_review | 0.4 | 0.9 | 0.2 | 0.3 | 0.1 |

`effective_trait = clamp(baseline × weight × 2, 0, 1)`

### 3.2 DynamicAdjuster — EMA 平滑 + 四条规则

**EMA（对话系统专家 #1）**：`new = current × (1-α) + target × α`，α=0.3

| 规则 | 触发 | 调整 |
|------|------|------|
| 对话深度 | turns > 3 | O +0.02/轮 |
| 负面情绪 | "angry/生气/烦" | A +0.1, N +0.05 |
| 决策语境 | "decide/选择/决定" | C +0.1, O -0.05 |
| 技术语境 | "code/代码/调试" | C +0.1, O -0.03 |

### 3.3 PersonalityInjector — 自然语言画像

**人格画像叙述（提示词工程师 #2）**：参数值 → 自然语言 persona description

```
高开放性 (>0.65): "You are naturally curious and open-minded..."
中开放性 (0.35-0.65): "You balance curiosity with practicality..."
低开放性 (<0.35): "You prefer established methods..."
```

**交叉效应（心理学专家 #3）**：7 组高影响力维度组合：
高O+高E=探索型社交 / 高O+高C=创意执行者 / 高C+高N=完美主义 /
高A+高E=自然连接者 / 高O+低N=创造性无畏 / 低E+高O=深度思考者 / 低A+高C=严谨直率

### 3.4 ConsistencyChecker

检测响应中期望词汇命中率，0-100 分，<40 分标记不一致。

## 四、文件与测试

| 文件 | 变更 |
|------|------|
| `packages/MetaSoul/personality/personality_matrix.py` | **新建** |
| `packages/MetaSoul/personality/consistency_checker.py` | **新建** |
| `packages/ZenAgent/core.py` | **修改** |
| `packages/MetaSoul/tests/test_personality_matrix.py` | **新建** |

预计 ~18 测试，验证方式：`pytest packages/MetaSoul/tests/test_personality_matrix.py -v`
