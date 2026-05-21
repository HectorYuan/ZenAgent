# M8.5: ZenAgent CLI + TUI 设计文档

**日期**: 2026-05-21
**参考**: ZenSkill TUI/CLI 模式 + ZenAgent 22 组能力

---

## 一、技术选型

| 层 | 技术 | 理由 |
|---|------|------|
| CLI | 原生 `argparse` | 与 ZenSkill 一致，零额外依赖 |
| TUI | Textual ≥ 0.40 | 成熟 Textual 框架 |
| Light TUI | Rich 命令模式 | 非 TTY 终端降级方案 |
| 数据层 | ZenaDataAdapter | 统一接口，屏幕不直接调系统 API |
| 命令元数据 | CommandRegistry | 声明式，同时驱动 CLI + TUI |

## 二、CLI 命令结构（13 个顶级子命令）

`chat / status / memory / personality / knowledge / provider / cache / agent / config / doctor`

## 三、TUI 屏幕（6 屏）

| 键 | 屏幕 | 对应 CLI 组 |
|----|------|------------|
| `0` | ChatScreen | chat |
| `1` | DashboardScreen | status + doctor |
| `2` | MemoryScreen | memory + knowledge |
| `3` | PersonalityScreen | personality |
| `4` | LearnScreen | learning + reflect |
| `5` | InfraScreen | provider + agent + task |

全局交互: `/` 命令面板, `Ctrl+R` 刷新, `Tab` 焦点, `q` 退出, `F1` 帮助

## 四、文件规划

```
packages/ZenAgent/zena/
├── __init__.py / __main__.py    # CLI 入口
├── cli_utils.py                 # 格式化工具
├── core/adapter.py              # 数据适配器
├── core/commands.py             # 命令注册表
├── tui/app.py                   # Textual App
├── tui/screens/*.py             # 6 个屏幕
└── tests/
```

## 五、验证

```bash
python -m packages.ZenAgent.zena chat "Hello"
python -m packages.ZenAgent.zena status
python -m packages.ZenAgent.zena personality show
python -m packages.ZenAgent.zena --json status
```
