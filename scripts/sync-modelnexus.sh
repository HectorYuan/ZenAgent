#!/usr/bin/env bash
# sync-modelnexus.sh — ModelNexus 子模块同步脚本
# 用法: ./scripts/sync-modelnexus.sh

set -e

SUBMODULE="packages/modelnexus"

echo "=== ModelNexus 子模块同步 ==="

# 1. 拉取子模块最新
git submodule update --init --recursive

# 2. 进入子模块
cd "$SUBMODULE"

# 3. 获取远程变更
git fetch origin main

# 4. 检查是否有本地变更
if ! git diff-index --quiet HEAD --; then
    echo "[!] 检测到本地未提交变更:"
    git status --short
    echo "    请先提交或暂存变更。"
    exit 1
fi

# 5. 合并远程
echo "[*] 拉取 origin/main..."
git pull origin main

# 6. 回到主仓库
cd ../..

# 7. 更新子模块引用
if git diff --name-only | grep -q "$SUBMODULE"; then
    git add "$SUBMODULE"
    git commit -m "chore: update modelnexus submodule to latest"
    echo "[OK] 子模块引用已更新"
else
    echo "[OK] 子模块已是最新"
fi
