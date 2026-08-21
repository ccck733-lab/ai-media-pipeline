"""步骤2：写脚本 + 去AI + 安全审查。

无外部模型依赖即可运行：基于模板渲染初稿，并附带去AI自检清单与安全审查报告。
（若要接 LLM 自动生成，可在 script_writer.model 配置端点，由 WorkBuddy 会话驱动。）
"""
from pipeline.steps import step_dir, save, read, prompt_path, ROOT


def render(template: str, acc: dict, topic: str, style: str) -> str:
    out = template
    out = out.replace("{{niche}}", acc.get("niche", ""))
    out = out.replace("{{topic}}", topic)
    out = out.replace("{{length}}", str(acc.get("target_length_sec", 60)))
    out = out.replace("{{style}}", style or "（无风格参考，请补充 config/style 下文件）")
    return out


def safety_report(checklist: str, topic: str) -> str:
    items = [l.strip("- ").strip() for l in checklist.splitlines() if l.strip().startswith("-")]
    lines = [f"# 安全审查报告 — 选题: {topic}\n"]
    lines.append("逐项人工确认（✅ 通过 / ⚠️ 需修改 / ❌ 禁止发布）：\n")
    for it in items:
        if it:
            lines.append(f"- [ ] {it}")
    lines.append("\n审查结论: _________________  审查人: __________")
    return "\n".join(lines)


def run(cfg: dict, ctx: dict) -> dict:
    acc = cfg["account"]
    sw = cfg.get("script_writer", {})
    work = step_dir(ctx["account_name"], "script_writing")
    topic = ctx.get("topic") or "（未提供 --topic，请在运行命令追加 --topic \"你的选题\"）"
    template = read(prompt_path("script_template.md"))
    deai = read(prompt_path("de_ai_rules.md"))
    safety = read(prompt_path("safety_checklist.md"))
    style_path = acc.get("style_ref")
    style = read(ROOT / style_path) if style_path else ""

    script = render(template, acc, topic, style)
    if style:
        script = f"<!-- 人设约束（来自风格复刻文件，写稿时严格对齐） -->\n{style}\n\n---\n\n{script}"
    save(work / "script.md", script)
    notes = [f"已生成脚本初稿 -> {work / 'script.md'}"]
    if sw.get("de_ai"):
        save(work / "de_ai_checklist.md", deai)
        notes.append("已附加去AI自检清单（交付前逐项过）")
    if sw.get("safety_review"):
        save(work / "safety_report.md", safety_report(safety, topic))
        notes.append("已生成安全审查报告（含待确认项）")
    return {"status": "已生成脚本+审查", "notes": notes}
