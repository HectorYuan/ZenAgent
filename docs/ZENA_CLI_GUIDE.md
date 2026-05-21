# ZenAgent CLI 使用指南

**版本**: v1.0.0
**更新**: 2026-05-21

---

## 快速开始

```bash
# 三种启动方式，任选其一
./zena chat "Hello"                       # 项目根目录简命令 (推荐)
python -m packages.ZenAgent.zena status   # Python 模块方式
zena doctor                               # pip install -e . 后全局可用
```

## 命令参考

### 1. chat — AI 对话

```bash
# 单次问答
./zena chat "What is Python?"

# 带系统提示
./zena chat "分析这段代码" --system-prompt "你是一位资深软件工程师"

# 交互模式（持续对话，q 退出）
./zena chat

# 交互模式内部命令:
#   clear  - 清空对话历史
#   q      - 退出
```

### 2. status — 系统状态

```bash
# 完整状态仪表盘
./zena status

# JSON 输出（脚本集成）
./zena --json status | jq .intent_router
```

### 3. memory — 记忆管理

```bash
# 存储记忆
./zena memory add "Python is a versatile language" --type EPISODIC

# 搜索记忆
./zena memory search "Python"

# 记忆统计
./zena memory stats
```

### 4. personality — 人格管理

```bash
# 查看 Big Five
./zena personality show

# 输出示例:
#   openness             ████████████████████████████░░ 0.82
#   conscientiousness    ██████████████░░░░░░░░░░░░░░░░ 0.45
#   extraversion         ██████████████████████░░░░░░░░ 0.72
#   agreeableness        ████████████████████████████░░ 0.90
#   neuroticism          ██████░░░░░░░░░░░░░░░░░░░░░░░░ 0.18

# 调整特质
./zena personality set openness 0.85

# 场景列表
./zena personality scenario
```

### 5. knowledge — 知识库

```bash
# 搜索 SPO 三元组
./zena knowledge search "Python"

# 知识库统计
./zena knowledge stats
```

### 6. provider — Provider 管理

```bash
# 列出可用 Provider
./zena provider list

# Provider 健康状态（含熔断器状态）
./zena provider health
```

### 7. agent — Agent 管理

```bash
./zena agent list
```

### 8. doctor — 健康检查

```bash
./zena doctor

# 输出:
#   🟢 agent           ZenAgent
#   🟢 llm             llm
#   🔴 memory          memory  ← 子系统未初始化
#   🟢 personality     personality
#   🟢 runtime         runtime
```

---

## JSON 模式（脚本集成）

所有命令支持 `--json` 标志，输出纯 JSON：

```bash
./zena --json status | jq .
./zena --json memory search "Python" | jq '.[].content'
./zena --json personality show | jq '.openness'
```

---

## 输出格式约定

| 元素 | 示例 |
|------|------|
| 状态指示器 | 🟢正常 🟡警告 🔴异常 ⚪未启用 |
| 条形图 | `████████████████░░░░░░░░` (比例可视化) |
| 层标识 | 📊L0 📡L1 🧘L2 🧠L3 🕊L4 |
| 空状态 | `[no data] 没有匹配的记忆。→ zena memory add <content>` |

---

## 安装为系统命令

```bash
# 方式 A: pip 可编辑安装（推荐）
pip install -e .
zena status

# 方式 B: 软链接
ln -s $(pwd)/zena /usr/local/bin/zena
zena doctor

# 方式 C: 别名
alias zena='python -m packages.ZenAgent.zena'
```
