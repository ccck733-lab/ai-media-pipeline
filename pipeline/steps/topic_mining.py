"""步骤1：数据化选题 / 拆解爆款（Agent Reach / MediaCrawler 接入）。

检测到 MediaCrawler 工程时，生成可直接运行的爬取脚本（含 cookies 配置说明）；
未配置时降级为研究简报，交给 WorkBuddy 分析。绝不自动爬取——需用户本人账号与授权。
"""
from pipeline.steps import step_dir, save, read, external_exists, ROOT


def build_run_script(cfg: dict, ctx: dict) -> str:
    tm = cfg.get("topic_mining", {})
    path = tm.get("mediacrawler_path", "")
    source = tm.get("source", "mediacrawler")
    keywords = tm.get("keywords", [])
    top_n = tm.get("top_n", 10)
    kw = " ".join(f'"{k}"' for k in keywords) or '"请填关键词"'
    return f"""#!/usr/bin/env bash
# 选题爬取脚本（由编排器生成）— 运行前请先按 MediaCrawler 文档配置 cookies/账号
set -e
cd "{path}"

# 1) 先看本机实际支持的参数（不同版本差异大，以 --help 为准）
python main.py --help || true

# 2) 交互模式（最稳）：直接 python main.py，按菜单选平台/类型/关键词
#    python main.py

# 3) 非交互示例（若 --help 显示支持下列参数，可取消注释使用）：
#    python main.py \\
#      --platform {source} \\
#      --type search \\
#      --keywords {kw} \\
#      --start 1 --end {top_n}

echo "爬取结果默认写入 MediaCrawler 的 db/ 目录；"
echo "请导出为 CSV/JSON 后，交给 WorkBuddy 做爆款拆解与选题排序。"
"""


def run(cfg: dict, ctx: dict) -> dict:
    tm = cfg.get("topic_mining", {})
    work = step_dir(ctx["account_name"], "topic_mining")
    notes = []
    path = tm.get("mediacrawler_path", "")

    # 始终产出研究简报（无爬取条件时给 WorkBuddy 用）
    brief = f"""# 选题研究简报（账号: {ctx['account_name']}）

关键词: {', '.join(tm.get('keywords', [])) or '(空)'}
目标条数: {tm.get('top_n', 10)}
来源: {tm.get('source', 'mediacrawler')}

任务（交给 WorkBuddy 或爬取工具）:
1. 找近 7 天同赛道高互动内容，列出标题/钩子/结构。
2. 拆 3 条爆款的"前3秒+信息密度+结尾互动"。
3. 输出 5 个可拍选题，按"契合度×差异化"排序。
"""
    save(work / "RESEARCH_BRIEF.md", brief)
    notes.append("已生成选题研究简报 -> RESEARCH_BRIEF.md")

    if external_exists(path):
        save(work / "RUN_MEDIACRAWLER.sh", build_run_script(cfg, ctx))
        notes.append(f"已生成可运行爬取脚本 -> RUN_MEDIACRAWLER.sh（cd 进 {path} 执行）")
        notes.append("运行前必须按 MediaCrawler 文档配置 cookies/账号，并遵守平台 ToS。")
        return {"status": "已生成爬取脚本", "notes": notes}
    else:
        notes.append(f"未配置爬取工具路径（topic_mining.mediacrawler_path={path or '(空)'}），"
                     "可用研究简报先让 WorkBuddy 分析选题。")
        return {"status": "已生成研究简报", "notes": notes}
