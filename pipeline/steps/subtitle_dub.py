"""步骤3：字幕 / 配音（pyvideotrans）。

未配置时降级为执行指引。pyvideotrans 支持视频翻译、配音、字幕。
"""
from pipeline.steps import step_dir, save, external_exists


def run(cfg: dict, ctx: dict) -> dict:
    sd = cfg.get("subtitle_dub", {})
    work = step_dir(ctx["account_name"], "subtitle_dub")
    path = sd.get("pyvideotrans_path", "")
    engine = sd.get("engine", "pyvideotrans")
    tgt = sd.get("target_lang", "en")
    notes = []
    if external_exists(path):
        notes.append(f"检测到 {engine}: {path}")
        notes.append(f"对 video_gen 产出视频执行 {tgt} 字幕配音（其 GUI/CLI 操作）。")
        return {"status": "待执行配音", "notes": notes}
    guide = f"""# 字幕配音执行指引（{engine}）

目标语言: {tgt}
输入: workspace/{ctx['account_name']}/video_gen/ 产出的成片
工具: PyVideoTrans（开源，支持识别+翻译+配音+字幕）

## 操作
1. 打开 PyVideoTrans，载入成片。
2. 选择源语言与翻译目标语言({tgt})。
3. 选择配音音色（建议与账号人设一致）。
4. 导出带字幕/配音版本到 workspace/{ctx['account_name']}/subtitle_dub/。

未检测到 pyvideotrans_path，请先在账号配置中填写正确路径。
"""
    save(work / "DO_SUBTITLE_DUB.md", guide)
    notes.append("未配置 PyVideoTrans，已生成字幕配音执行指引。")
    return {"status": "已生成执行指引", "notes": notes}
