---
name: style-replication
summary: 风格复刻长效技能——从爆款样本中收敛账号人设与脚本口吻
read_when:
  - 写脚本、复盘爆款、维护 config/style 风格文件时
type: long-term-skill
---

# 风格复刻（Style Replication）

## 目的
让每个账号的产出稳定贴合其"人设"，而不是每次都重新摸索语气。

## 工作流
1. 收集样本：把表现好的视频 transcript 追加到 `config/style/<account>.md` 的样本库。
2. 抽取规律：归纳钩子方式、节奏、常用词、禁用的 AI 腔。
3. 写稿约束：脚本必须引用风格文件作为 few-shot，口吻对齐样本。
4. 闭环：复盘评论后，若某类口吻更受欢迎，更新风格文件，剔除低效表达。

## 输出
- 更新后的 `config/style/<account>.md`
- 作为 script_writing 步骤的 `style_ref` 输入

## 注意
风格文件只存可复用的表达方式，不存可识别个人身份信息；样本需来自自有或已授权内容。
