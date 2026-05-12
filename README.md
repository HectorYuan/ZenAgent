# ZenAgent - 独立运行智能体平台

## 项目简介

ZenAgent 是一个基于 Monorepo 架构的智能体平台，旨在构建从底层基础设施到上层应用的完整智能体生态系统。平台采用分层设计，包括 LLM 基础设施层、运行时层、智能体层、集群管理层和灵魂团队层。

## Monorepo 结构

```
/root/ZenAgent/
├── packages/                    # 核心包目录
│   ├── LLMInfra/               # L0: LLM 基础设施层
│   ├── Runtime/                # L1: 运行时层
│   ├── ZenAgent/               # L2: 智能体层
│   ├── SwarmFly/               # L3: 集群管理层
│   └── SoulTeam/               # L4: 灵魂团队层
├── tests/                      # 共享测试目录
├── docs/                       # 文档目录
├── config/                     # 配置目录
├── pyproject.toml              # Poetry 配置
└── README.md                   # 项目说明
```

## Packages 目录说明

| 包名 | 层级 | 说明 |
|------|------|------|
| LLMInfra | L0 | LLM 基础设施，提供大语言模型调用接口封装 |
| Runtime | L1 | 运行时层，管理智能体执行环境和资源调度 |
| ZenAgent | L2 | 智能体核心，定义智能体基本行为和生命周期 |
| SwarmFly | L3 | 集群管理，处理多智能体协作和任务分发 |
| SoulTeam | L4 | 灵魂团队层，提供高级团队协作和决策能力 |

## 开发指南

### 环境要求

- Python >= 3.10
- Poetry >= 1.6.0

### 安装依赖

```bash
# 安装所有依赖
poetry install

# 安装开发依赖
poetry install --with dev
```

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行特定包的测试
poetry run pytest packages/SwarmFly/tests/
```

### 包管理

```bash
# 添加新依赖到根项目
poetry add package-name

# 添加依赖到特定包
cd packages/<package-name>
poetry add package-name
```

## 相关文档

- [项目计划](./项目计划/ZenAgent独立运行平台项目计划_v2.2.md)
- [SwarmFly 源码](./packages/SwarmFly/)
- [API 文档](./packages/SwarmFly/API文档.md)

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。
