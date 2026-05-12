# Feature Flag 命名规范

> **版本**: v1.1
> **创建日期**: 2026-04-28
> **状态**: 已批准

---

## 1. 规范概述

### 1.1 目的
统一SwarmFly项目中的Feature Flag命名规范，消除`enableSwarm`/`ENABLE_SWARM`混用问题。

### 1.2 适用范围
- 所有Feature Flag定义
- 环境变量配置
- 配置文件中的功能开关
- 代码中的功能检测

---

## 2. 命名规范

### 2.1 命名风格
**统一采用 SCREAMING_SNAKE_CASE（全大写下划线分隔）**

| ✅ 正确 | ❌ 错误 |
|--------|--------|
| `ENABLE_SWARM` | `enableSwarm` |
| `ENABLE_SWARM` | `EnableSwarm` |
| `ENABLE_SWARM` | `ENABLE-SWARM` |
| `ENABLE_FEATURE_X` | `enable_feature_x` |
| `DISABLE_DEBUG_MODE` | `disableDebugMode` |

### 2.2 命名组成

```
{PREFIX}_{MODULE}_{FEATURE}
```

| 部分 | 说明 | 示例 |
|------|------|------|
| PREFIX | 前缀 | `ENABLE`, `DISABLE`, `FEATURE`, `MODE` |
| MODULE | 模块名 | `SWARM`, `AGENT`, `ROUTER`, `CACHE` |
| FEATURE | 功能名 | `FLY`, `HANDOFF`, `METRICS`, `DEBUG` |

### 2.3 完整示例

```python
# SwarmFly Feature Flags
ENABLE_SWARM_FLY = True
ENABLE_SWARM_HANDOFF = True
ENABLE_SWARM_ROUTING = True

DISABLE_SWARM_DEBUG = False
FEATURE_SWARM_NEW_ALGORITHM = False

MODE_SWARM_TEST = False
```

---

## 3. 配置示例

### 3.1 YAML配置

```yaml
# ✅ 正确格式
feature_flags:
  enable_swarm_fly: true
  enable_swarm_handoff: true
  disable_swarm_debug: false

# ❌ 错误格式
feature_flags:
  enableSwarm: true        # 驼峰命名
  ENABLE_SWARM: true       # 与键名重复
  enable-swarm: true       # 中划线分隔
```

### 3.2 环境变量

```bash
# ✅ 正确格式
export ENABLE_SWARM_FLY=1
export ENABLE_SWARM_HANDOFF=1
export DISABLE_SWARM_DEBUG=0

# ❌ 错误格式
export enableSwarm=1           # 驼峰命名
export ENABLE_SWARM=1         # 缺少模块名
export enable-swarm-fly=1     # 中划线分隔
```

### 3.3 Python代码

```python
# ✅ 正确格式
from swarmfly.config import FeatureFlags

if FeatureFlags.ENABLE_SWARM_FLY:
    # ...

if not FeatureFlags.DISABLE_SWARM_DEBUG:
    logger.debug("Debug mode is disabled")

# ❌ 错误格式
if config.get('enableSwarm'):       # 驼峰
    # ...

if ENABLE_SWARM:                     # 缺少模块名
    # ...
```

---

## 4. 定义列表

### 4.1 SwarmFly核心Feature Flags

| Flag名称 | 默认值 | 说明 |
|----------|--------|------|
| `ENABLE_SWARM_FLY` | `True` | 启用FLY核心功能 |
| `ENABLE_SWARM_HANDOFF` | `True` | 启用智能体交接 |
| `ENABLE_SWARM_ROUTING` | `True` | 启用智能路由 |
| `ENABLE_SWARM_METRICS` | `True` | 启用指标收集 |
| `DISABLE_SWARM_DEBUG` | `False` | 禁用调试模式 |
| `DISABLE_SWARM_LOGGING` | `False` | 禁用日志输出 |

### 4.2 模块级Feature Flags

| Flag名称 | 默认值 | 说明 |
|----------|--------|------|
| `ENABLE_AGENT_POOL` | `True` | 启用智能体池 |
| `ENABLE_TASK_QUEUE` | `True` | 启用任务队列 |
| `ENABLE_ROUTER_CACHE` | `True` | 启用路由缓存 |
| `ENABLE_RESULT_AGGREGATION` | `True` | 启用结果聚合 |
| `FEATURE_NEW_ROUTING_ALGO` | `False` | 新路由算法(测试) |
| `FEATURE_ADAPTIVE_THRESHOLD` | `False` | 自适应阈值(测试) |

### 4.3 环境级Feature Flags

| Flag名称 | 默认值 | 说明 |
|----------|--------|------|
| `MODE_SWARM_TEST` | `False` | 测试模式 |
| `MODE_SWARM_DEV` | `False` | 开发模式 |
| `MODE_SWARM_PROD` | `False` | 生产模式 |
| `FEATURE_SWARM_ALPHA` | `False` | Alpha特性 |
| `FEATURE_SWARM_BETA` | `False` | Beta特性 |

---

## 5. 检查工具

### 5.1 lint_feature_flags.py

```python
"""
Feature Flag命名检查脚本

检测代码中的不一致命名
"""

import re
import os
from typing import List, Tuple

# 匹配驼峰命名
CAMEL_CASE_PATTERN = re.compile(r'[a-z]+[A-Z]')
# 匹配混合命名（数字+字母）
MIXED_CASE_PATTERN = re.compile(r'[a-z][A-Z]')

# 正确的SCREAMING_SNAKE_CASE模式
CORRECT_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]*[A-Z0-9]$')

FEATURE_FLAG_KEYWORDS = [
    'enable', 'disable', 'feature', 'mode', 'flag',
    'swarm', 'agent', 'router', 'cache'
]


def check_feature_flag_naming(text: str, file_path: str) -> List[Tuple[str, str]]:
    """
    检查Feature Flag命名
    
    Args:
        text: 待检查文本
        file_path: 文件路径
        
    Returns:
        问题列表 [(错误类型, 描述)]
    """
    issues = []
    lines = text.split('\n')
    
    for line_num, line in enumerate(lines, 1):
        # 跳过注释
        if line.strip().startswith('#'):
            continue
        
        # 检查驼峰命名
        camel_matches = CAMEL_CASE_PATTERN.findall(line)
        for match in camel_matches:
            if any(kw in match.lower() for kw in FEATURE_FLAG_KEYWORDS):
                issues.append((
                    'CAMEL_CASE',
                    f"{file_path}:{line_num} - Found camelCase '{match}'"
                ))
        
        # 检查混合命名
        for keyword in FEATURE_FLAG_KEYWORDS:
            pattern = rf'\b{keyword}[A-Z]'
            mixed_matches = re.findall(pattern, line, re.IGNORECASE)
            for match in mixed_matches:
                issues.append((
                    'MIXED_CASE',
                    f"{file_path}:{line_num} - Found mixed case '{match}'"
                ))
    
    return issues


def scan_directory(directory: str, extensions: List[str] = ['.py', '.yaml', '.yml']) -> List[Tuple[str, str]]:
    """
    扫描目录检查Feature Flag命名
    
    Args:
        directory: 目录路径
        extensions: 检查的文件扩展名
        
    Returns:
        问题列表
    """
    all_issues = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    issues = check_feature_flag_naming(content, file_path)
                    all_issues.extend(issues)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return all_issues


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Feature Flag命名检查")
    parser.add_argument("directory", help="要检查的目录")
    parser.add_argument("--fix", action="store_true", help="自动修复")
    
    args = parser.parse_args()
    
    issues = scan_directory(args.directory)
    
    if issues:
        print(f"Found {len(issues)} naming issues:\n")
        for issue_type, message in issues:
            print(f"[{issue_type}] {message}")
        return 1
    else:
        print("No naming issues found.")
        return 0


if __name__ == "__main__":
    exit(main())
```

---

## 6. CI集成

### 6.1 Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: feature-flag-naming
        name: Feature Flag Naming Check
        entry: python scripts/lint_feature_flags.py
        language: system
        types: [python, yaml]
        pass_filenames: false
        args: ['./Agents/SwarmFly']
```

### 6.2 GitHub Actions

```yaml
# .github/workflows/feature-flags.yml
name: Feature Flag Checks

on:
  pull_request:
    paths:
      - 'Agents/SwarmFly/**'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check Feature Flag Naming
        run: |
          python ./Agents/SwarmFly/S1_Evolution/Phase1_Fix/lint_feature_flags.py ./Agents/SwarmFly
```

---

## 7. 迁移指南

### 7.1 旧代码迁移

| 旧命名 | 新命名 |
|--------|--------|
| `enableSwarm` | `ENABLE_SWARM_FLY` |
| `ENABLE_SWARM` | `ENABLE_SWARM_FLY` |
| `DISABLE_SWARM` | `DISABLE_SWARM_FLY` |
| `swarmEnabled` | `ENABLE_SWARM_FLY` |
| `is_swarm_active` | `ENABLE_SWARM_FLY` |

### 7.2 迁移步骤

1. **识别所有Feature Flag引用**
   ```bash
   grep -r "enableSwarm\|ENABLE_SWARM\|swarmEnabled" ./Agents/SwarmFly --include="*.py"
   ```

2. **创建迁移映射表**
   ```python
   FLAG_MIGRATION_MAP = {
       'enableSwarm': 'ENABLE_SWARM_FLY',
       'ENABLE_SWARM': 'ENABLE_SWARM_FLY',
       'swarmEnabled': 'ENABLE_SWARM_FLY',
   }
   ```

3. **执行批量替换**
   ```python
   import re
   
   def migrate_feature_flags(content: str) -> str:
       for old, new in FLAG_MIGRATION_MAP.items():
           content = re.sub(rf'\b{old}\b', new, content)
       return content
   ```

4. **运行验证脚本确认**
   ```bash
   python lint_feature_flags.py ./Agents/SwarmFly
   ```

---

## 8. 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-04-28 | v1.0 | 初始版本创建 |
| 2026-04-28 | v1.1 | 添加CI集成和迁移指南 |

---

*维护者: 赛博游侠*
*下次审查: 2026-05-28*
