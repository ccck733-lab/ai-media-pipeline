"""步骤5：多平台分发。

各平台发布需对应授权（API/开放平台），编排器产出分发清单，发布动作由你或
合规 API 执行。注意遵守各平台内容规范与频率限制。
"""
from pipeline.steps import step_dir, save


def run(cfg: dict, ctx: dict) -> dict:
    d = cfg.get("distribution", {})
    work = step_dir(ctx["account_name"], "distribution")
    platforms = d.get("platforms", [])
    cron = d.get("schedule_cron", "")
    lines = [f"# 多平台分发清单 — {ctx['account_name']}\n"]
    lines.append(f"计划(cron): {cron}\n")
    for p in platforms:
        lines.append(f"## {p}")
        lines.append(f"- 成片: workspace/{ctx['account_name']}/subtitle_dub/")
        lines.append(f"- 标题/标签: 见 script_writing 产出")
        lines.append(f"- 发布前: 已过安全审查? (见 safety_report.md)")
        lines.append("")
    lines.append("发布后: 回写发布链接到 review 步骤做评论复盘。")
    save(work / "DISTRIBUTE_CHECKLIST.md", "\n".join(lines))
    notes = [f"已生成分发清单 -> {work / 'DISTRIBUTE_CHECKLIST.md'}"]
    notes.append(f"目标平台: {', '.join(platforms) or '(未配置)'}")
    return {"status": "已生成分发清单", "notes": notes}
