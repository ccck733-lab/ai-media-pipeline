"""步骤2：写脚本 + 去AI + 安全审查。

生成策略：
1. 若账号配置了 LLM（script_writer.model + base_url + api_key，OpenAI 兼容），
   直接调用生成真实脚本（markdown 结构化输出）。
2. 未配置 / 调用失败时，降级为「结构化模板初稿」：钩子 + 痛点 + 3 要点 + 结论 + 互动，
   保证一键流程始终能产出可读、可驱动画面的脚本。
"""
import json
import re
import urllib.request
from pipeline.steps import step_dir, save, read, prompt_path, ROOT


def _call_llm(sw: dict, system: str, user: str) -> str | None:
    """调用 OpenAI 兼容接口；任何异常返回 None（交由降级逻辑处理）。"""
    base = (sw.get("base_url") or "").strip()
    key = (sw.get("api_key") or "").strip()
    model = (sw.get("model") or "").strip()
    if not (base and key and model):
        return None
    try:
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.8,
        }).encode("utf-8")
        req = urllib.request.Request(
            base.rstrip("/") + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:  # noqa
        return f"__LLM_ERR__:{e}"


def _fallback_script(topic: str, acc: dict, style: str) -> str:
    """无 LLM 时的结构化初稿。内容用话题做合理泛化，明确标注是模板。"""
    hook = f"{topic} —— 但 90% 的人都理解错了。"
    pain = f"我观察了一圈，关于「{topic}」，大家最容易卡住的其实不是不懂，而是第一步就走偏了。"
    p1 = f"先说最常见的坑：大多数人一上来就去找「最快的方法」，反而忽略了最基础的那一步。"
    p2 = f"正确的打开方式很简单——把「{topic}」拆成你今天就能动手的一件小事，先完成再说。"
    p3 = f"再往前走一步：别追求一次做对，先跑起来、再迭代，比停在准备阶段强十倍。"
    conclusion = f"所以关于「{topic}」，记住一句话：先动起来，比想清楚更重要。"
    cta = "评论区告诉我你最想搞懂的下一个问题，下期接着讲。"
    return (
        f"# 脚本（{topic}）\n\n"
        f"> 生成方式：结构化模板初稿（未接入 LLM）。配置 script_writer.api_key 可升级为真实脚本。\n\n"
        f"## 钩子\n{hook}\n\n"
        f"## 痛点\n{pain}\n\n"
        f"## 正文\n1. {p1}\n2. {p2}\n3. {p3}\n\n"
        f"## 结论\n{conclusion}\n\n"
        f"## 互动\n{cta}\n"
    )


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
    topic = ctx.get("topic") or ""
    deai = read(prompt_path("de_ai_rules.md"))
    safety = read(prompt_path("safety_checklist.md"))
    style_path = acc.get("style_ref")
    style = read(ROOT / style_path) if style_path else ""

    if not topic:
        topic_disp = "（未提供 --topic，请在运行命令追加 --topic \"你的选题\"）"
        script = _fallback_script("你的选题", acc, style)
    else:
        topic_disp = topic
        system = ("你是抖音知识科普短视频脚本撰写者，口语、敢下判断、不堆砌排比、避免 AI 腔。"
                  + (f"\n人设与风格约束：\n{style}" if style else ""))
        user = (f"为选题「{topic}」写一份约 {acc.get('target_length_sec', 60)} 秒的短视频脚本，"
                f"严格按以下 markdown 结构输出，不要任何解释：\n"
                f"# 脚本（{topic}）\n## 钩子\n## 痛点\n"
                f"## 正文\n（用 1. 2. 3. 列出 3 个要点，每点一句口语化）\n"
                f"## 结论\n## 互动")
        llm_out = _call_llm(sw, system, user)
        if llm_out and not llm_out.startswith("__LLM_ERR__"):
            script = llm_out
        else:
            if llm_out and llm_out.startswith("__LLM_ERR__"):
                save(work / "llm_error.log", f"LLM 调用失败，已降级为模板初稿：{llm_out}\n")
            script = _fallback_script(topic, acc, style)

    if style:
        script = f"<!-- 人设约束（来自风格复刻文件，写稿时严格对齐） -->\n{style}\n\n---\n\n{script}"
    save(work / "script.md", script)
    notes = [f"已生成脚本 -> {work / 'script.md'}"]
    if sw.get("de_ai"):
        save(work / "de_ai_checklist.md", deai)
        notes.append("已附加去AI自检清单（交付前逐项过）")
    if sw.get("safety_review"):
        save(work / "safety_report.md", safety_report(safety, topic_disp))
        notes.append("已生成安全审查报告（含待确认项）")
    return {"status": "已生成脚本+审查", "notes": notes}
