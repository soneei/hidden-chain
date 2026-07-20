#!/bin/bash
# Hidden Chain — GitHub 推送脚本
# 先建仓库再推代码，跑一次就行

set -e

REPO_NAME="hidden-chain"
REPO_DIR="/Users/sona/Projects/hidden-chain"
GITHUB_USER="soneei"

echo "1. 检查 gh CLI..."
if ! command -v gh &>/dev/null; then
  echo "   gh 未安装，正在安装..."
  if command -v brew &>/dev/null; then
    brew install gh
  else
    echo "   请手动安装 gh CLI: https://cli.github.com/"
    exit 1
  fi
fi

echo "2. 检查 GitHub 登录..."
if ! gh auth status &>/dev/null; then
  echo "   未登录，可能需要运行: gh auth login"
  gh auth login
fi

echo "3. 创建 GitHub 仓库..."
gh repo create "$GITHUB_USER/$REPO_NAME" --private --description "中医 + 穿戴数据审计的 HRV 分析引擎" --source "$REPO_DIR" --remote origin --push

echo ""
echo "✅ 完成！仓库地址: https://github.com/$GITHUB_USER/$REPO_NAME"
