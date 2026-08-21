#!/usr/bin/env python3
"""AI 自媒体自动化流水线编排器。

用法:
  python3 pipeline/orchestrator.py --account douyin-default --step all
  python3 pipeline/orchestrator.py --account douyin-default --step script_writing --topic "为什么房价在跌"
  python3 pipeline/orchestrator.py --list-accounts

外部工具（MediaCrawler / PyVideoTrans / Remotion）未安装时，对应步骤会优雅降级：
产出"可执行下一步指引"文件，把机械动作交给工具、把创作动作交给 WorkBuddy。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.steps import (  # noqa: E402
    topic_mining,
    script_writing,
    subtitle_dub,
    video_gen,
    distribution,
    review,
)

REGISTRY = {
    "topic_mining": topic_mining,
    "script_writing": script_writing,
    "subtitle_dub": subtitle_dub,
    "video_gen": video_gen,
    "distribution": distribution,
    "review": review,
}


def load_account(name: str) -> dict:
    p = ROOT / "config" / "accounts" / f"{name}.json"
    if not p.exists():
        sys.exit(f"[错误] 找不到账号配置: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_pipeline() -> dict:
    return json.loads((ROOT / "config" / "pipeline.json").read_text(encoding="utf-8"))


def list_accounts() -> None:
    d = ROOT / "config" / "accounts"
    for f in sorted(d.glob("*.json")):
        print(" -", f.stem)


def main():
    ap = argparse.ArgumentParser(description="AI 自媒体自动化流水线")
    ap.add_argument("--account", help="账号配置名（不含 .json）")
    ap.add_argument("--step", default="all", help="步骤名 或 all")
    ap.add_argument("--topic", default="", help="供脚本步骤使用的选题文本")
    ap.add_argument("--list-accounts", action="store_true")
    args = ap.parse_args()

    if args.list_accounts:
        list_accounts()
        return

    if not args.account:
        sys.exit("请传入 --account <name>，或 --list-accounts 查看可用账号。")

    cfg = load_account(args.account)
    pipe = load_pipeline()
    steps = pipe["pipeline"]["steps"] if args.step == "all" else [args.step]

    ctx = {"root": ROOT, "topic": args.topic, "account_name": args.account}

    print(f"== 流水线: {pipe['pipeline']['name']} | 账号: {args.account} ==")
    for s in steps:
        mod = REGISTRY.get(s)
        if not mod:
            print(f"[跳过] 未知步骤: {s}")
            continue
        print(f"\n--- 步骤: {s} ---")
        try:
            result = mod.run(cfg, ctx)
            status = result.get("status", "?")
            print(f"状态: {status}")
            for line in result.get("notes", []):
                print("  •", line)
        except Exception as e:  # noqa
            print(f"[异常] {s}: {e}")

    print("\n完成。产出文件见 workspace/" + args.account + "/")


if __name__ == "__main__":
    main()
