#!/bin/bash
# ZenAgent GitHub 仓库初始化脚本
# 使用方法: ./scripts/init-github-repo.sh <github-token>

set -e

GITHUB_TOKEN=${1:-$GITHUB_TOKEN}
REPO_NAME="ZenAgent"
REPO_DESC="ZenAgent - Agent 智能体集群完全独立运行平台"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "请提供 GitHub Token"
    echo "使用方式: ./scripts/init-github-repo.sh <github-token>"
    exit 1
fi

echo "开始创建 GitHub 仓库..."

# 创建远程仓库
RESPONSE=$(curl -s -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/user/repos \
    -d "{\"name\":\"$REPO_NAME\",\"description\":\"$REPO_DESC\",\"private\":false,\"has_issues\":true,\"has_wiki\":true}")

USERNAME=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep -o '"login": "[^"]*' | cut -d'"' -f4)
REPO_URL="https://github.com/$USERNAME/$REPO_NAME"

echo "仓库地址: $REPO_URL"

# 添加远程仓库
git remote remove origin 2>/dev/null || true
git remote add origin "https://$GITHUB_TOKEN@github.com/$USERNAME/$REPO_NAME"

echo "推送代码..."
git branch -M main
git push -u origin main --tags

echo "完成!"
