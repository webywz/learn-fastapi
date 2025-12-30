---
name: commit
description: 生成规范的 git commit 提交信息，遵循 Conventional Commits 规范。当用户需要提交代码、生成提交信息时使用。
allowed-tools: Bash(git:*)
---

# Git Commit 助手

## 概述

帮助生成规范的 git commit 信息，遵循 Conventional Commits 规范。

## 执行步骤

当用户请求提交代码时：

1. **检查状态**: 运行 `git status` 查看变更文件
2. **查看差异**: 运行 `git diff --staged` 和 `git diff` 查看具体变更
3. **查看历史**: 运行 `git log --oneline -5` 了解项目提交风格
4. **生成提交信息**: 根据变更内容生成规范的提交信息
5. **执行提交**: 添加文件并提交

## 提交类型

| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档变更 |
| style | 代码格式（不影响代码运行的变动） |
| refactor | 重构（既不是新功能也不是修复 bug） |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建过程或辅助工具的变动 |
| ci | CI/CD 配置变更 |

## 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 规则

1. **标题行**（第一行）:
   - 使用祈使语气
   - 不超过 50 个字符
   - 结尾不加句号
   - 可以使用中文或英文

2. **正文**（可选）:
   - 与标题空一行
   - 说明 what 和 why，而不是 how
   - 每行不超过 72 个字符

3. **页脚**（可选）:
   - 关联 issue: `Fixes #123` 或 `Closes #456`
   - 破坏性变更: `BREAKING CHANGE: 描述`

## 示例

### 简单修复
```
fix(auth): 修复登录重定向循环问题
```

### 新功能
```
feat(api): 添加用户分页查询接口

实现基于游标的分页功能，支持自定义每页数量
```

### 文档更新
```
docs: 添加 API 中文描述

为任务相关 API 端点添加中文 summary 和 description
```

## 执行命令

```bash
# 添加文件
git add <files>

# 提交（使用 HEREDOC 确保格式正确）
git commit -m "$(cat <<'EOF'
<commit message>
EOF
)"

# 验证提交
git status
```

## 注意事项

- 提交前确认暂存的文件是否正确
- 不要提交敏感文件（.env, credentials.json 等）
- 不要使用 `--amend` 除非用户明确要求
- 不要自动 push，除非用户明确要求
