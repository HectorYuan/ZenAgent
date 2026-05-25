# 子模块同步指南

## 架构

```
ZenAgent (主仓库)
├── packages/modelnexus (子模块 → github.com/HectorYuan/modelnexus)
└── packages/* (主仓库代码)
```

## 日常操作

### 拉取子模块最新

```bash
git submodule update --init --recursive
cd packages/modelnexus && git pull origin main
```

### 提交子模块变更

```bash
cd packages/modelnexus
git add .
git commit -m "fix: ..."
git push origin main

# 回到主仓库更新引用
cd ../..
git add packages/modelnexus
git commit -m "chore: update modelnexus submodule"
git push
```

### 同步脚本（一键）

```bash
./scripts/sync-modelnexus.sh
```

## 子模块技术债

剩余 7 项在 modelnexus 内：

| 项 | 文件 | 说明 |
|----|------|------|
| CORS | main.py, main_v3.py, settings.py | `allow_origins=[*]` → env var |
| ContextAwareRouter | context_aware_router.py | TODO 改注释 |
| System.core 死代码 | main.py | 移除不存在的外部 import |
| security 测试 | security/* (4 files) | 需要 Mock |
| observability stub | observability/* (3 files) | NotImplementedError → warning |
| Phase 标记 | 30+ files | 注释清理 |

## 主仓库引用

主仓库 `.gitmodules` 指向 modelnexus 仓库的主分支。
