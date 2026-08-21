"""步骤6：评论复盘 -> 选题迭代（闭环）。

抓取评论、归纳反馈、反哺下一轮 topic_mining。这是流程自优化的数据入口。
"""
from pipeline.steps import step_dir, save


def run(cfg: dict, ctx: dict) -> dict:
    r = cfg.get("review", {})
    work = step_dir(ctx["account_name"], "review")
    notes = []
    if r.get("scrape_comments"):
        prompt = f"""# 评论复盘分析（交给 WorkBuddy 或 MediaCrawler 评论模块）

账号: {ctx['account_name']}
任务:
1. 抓取最近发布视频的评论（需账号授权/合规方式）。
2. 归纳高频问题、情绪倾向、完播/互动信号。
3. 输出 3 条对下一轮选题的修改建议。
4. 把有效建议写回 config/style/ 对应风格文件，收敛人设。
"""
        save(work / "COMMENT_REVIEW.md", prompt)
        notes.append("已生成评论抓取分析 prompt。")
    if r.get("iterate"):
        save(work / "ITERATE.md",
             "# 选题迭代\n将复盘结论转为下轮 topic_mining 的 keywords/niche 调整，"
             "并更新 config/accounts 对应配置。\n")
        notes.append("已生成选题迭代模板（复盘后回灌选题）。")
    return {"status": "已生成复盘模板", "notes": notes}
