# AI 自媒体自动化工作流（WorkBuddy 编排）

基于你描述的 6 步闭环 + 三类长效技能的**可运行骨架**。核心思想：配置驱动、
按账号克隆；外部工具缺失时优雅降级，把机械动作交给工具、创作/把关动作交给 WorkBuddy。

## 流程地图

```
1. 选题拆解   Agent Reach / MediaCrawler  ──► RESEARCH_BRIEF
2. 写脚本     + 去AI + 安全审查            ──► script.md / safety_report.md
3. 字幕配音   pyvideotrans                 ──► 带字幕/配音成片
4. 视频画面   Remotion / Hyperframes       ──► 成片
5. 多平台分发 各平台授权 API               ──► DISTRIBUTE_CHECKLIST
6. 评论复盘   ──► 反哺 1（闭环）            ──► COMMENT_REVIEW / ITERATE
        │
        └─ 长效技能: 风格复刻 · 流程自优化 · 安全审查
```

## 目录结构
```
ai-media-pipeline/
├── config/
│   ├── pipeline.json            # 全局步骤顺序
│   ├── accounts/*.json          # 每个账号一套（抖音/YouTube 示例）
│   └── style/*.md               # 风格复刻参考（人设/样本库）
├── pipeline/
│   ├── orchestrator.py          # CLI 编排器（纯标准库，零依赖）
│   └── steps/                   # 6 个步骤模块
├── prompts/                     # 脚本模板 / 去AI规则 / 安全清单
├── skills/                      # 三类长效技能 SKILL.md（已复制到 ~/.workbuddy/skills/ 常驻）
├── video/remotion-app/          # 检测不到 Remotion 时自动生成的脚手架
└── workspace/<account>/         # 各步骤产出（运行后生成）
```

## 快速上手
```bash
# 0. 进目录
cd ai-media-pipeline

# 1. 看可用账号
python3 pipeline/orchestrator.py --list-accounts

# 2. 跑完整流水线（外部工具未装会降级并给指引）
python3 pipeline/orchestrator.py --account douyin-default --step all

# 3. 只写一版脚本（带选题）
python3 pipeline/orchestrator.py --account douyin-default --step script_writing --topic "为什么房价在跌"

# 4. 看产出
open workspace/douyin-default/script_writing/script.md
```

## 按账号配置（你提到的"先摸透单工具再按账号配置"）
1. 复制 `config/accounts/douyin-default.json` → 改名 `你的账号.json`。
2. 填 `topic_mining.mediacrawler_path`、`subtitle_dub.pyvideotrans_path`、
   `video_gen.remotion_project` 等真实路径（不填则对应步骤降级为指引）。
3. 在 `config/style/` 写一份你的风格文件，脚本步骤会引用它。
4. 调 `target_length_sec` / `keywords` / `platforms` 适配该账号。

## 三类长效技能（skills/）
- **风格复刻** `style-replication`：从爆款样本收敛人设，喂给脚本步骤。
- **流程自优化** `process-optimization`：用复盘数据反哺关键词/配置。
- **安全审查** `safety-review`：发布前合规与版权把关。
> 想让它们在 WorkBuddy 里长期可用：把 `skills/<name>` 复制到 `~/.workbuddy/skills/`。

## 诚实说明（哪些需要你自己的手）
- **爬取(Agent Reach/MediaCrawler)**：检测到工程后生成**可直接运行的 `RUN_MEDIACRAWLER.sh`**（含 cookies 配置与 `--help` 探参）；编排器不自动爬，运行需你本人账号并守平台 ToS。
- **pyvideotrans / Remotion**：检测到工程给构建命令；未检测到 Remotion 时自动生成 `video/remotion-app` 可运行脚手架（`npm install && npm run dev`）。
- **多平台分发**：发布需平台授权（开放平台 token / API），编排器产出清单，发布动作由你或合规 API 执行。
- **评论抓取**：需账号授权与合规方式；复盘 prompt 交给 WorkBuddy 或 MediaCrawler 评论模块。
- **三类长效技能**：已复制到 `~/.workbuddy/skills/`，在 WorkBuddy 中常驻可用（style-replication / process-optimization / safety-review）。

## 自动化
已配置 WorkBuddy 自动化「评论复盘 → 选题迭代」，按你设定周期跑第 6 步并回灌第 1 步。
