---
name: process-optimization
summary: 流程自优化长效技能——用复盘数据反哺选题与配置
read_when:
  - review 步骤之后、调整 pipeline 配置、决定下一轮选题时
type: long-term-skill
---

# 流程自优化（Process Self-Optimization）

## 目的
让流水线越跑越准：用评论/数据反馈自动调整关键词、时长、平台策略。

## 工作流
1. 采集信号：完播率、互动率、评论高频词（来自 review 步骤）。
2. 归因：哪类选题/结构表现好，哪类踩雷。
3. 调参：更新 `config/accounts/<account>.json` 的 keywords、target_length_sec、platforms。
4. 记录：在 `workspace/<account>/review/` 留迭代日志，避免重复试错。

## 触发
- 周期性自动化（见 WorkBuddy 自动化"评论复盘→选题迭代"）。
- 单次手动：跑 `--step review` 后调用本技能。

## 边界
只基于自有账号数据做优化；不跨账号盗用他人内容，不涉及平台规则规避。
