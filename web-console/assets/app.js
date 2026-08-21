// ===== 内嵌数据（与 config/ 保持一致；静态页无法读服务端文件，故内联）=====
const PIPELINE = {
  name: "ai-self-media-automation",
  steps: ["topic_mining", "script_writing", "subtitle_dub", "video_gen", "distribution", "review"]
};

const STEP_META = {
  topic_mining:    { label: "① 选题拆解",  desc: "Agent Reach / MediaCrawler 拆爆款" },
  script_writing:  { label: "② 写脚本",    desc: "去AI感 + 安全审查" },
  subtitle_dub:    { label: "③ 字幕配音",  desc: "PyVideoTrans" },
  video_gen:       { label: "④ 视频画面",  desc: "Remotion / Hyperframes" },
  distribution:    { label: "⑤ 多平台分发", desc: "抖音 / YouTube 等" },
  review:          { label: "⑥ 评论复盘",  desc: "反哺下一轮选题" }
};

const ACCOUNTS = {
  "douyin-default": {
    account: { platform: "douyin", name: "my-douyin", niche: "知识科普", style_ref: "config/style/douyin-style.md", target_length_sec: 60, language: "zh" },
    topic_mining: { source: "mediacrawler", mediacrawler_path: "/path/to/MediaCrawler", keywords: ["行业关键词1", "行业关键词2", "竞品账号"], top_n: 10 },
    script_writer: { model: "your-llm-endpoint-or-leave-empty-to-use-workbuddy", de_ai: true, safety_review: true },
    subtitle_dub: { engine: "pyvideotrans", pyvideotrans_path: "/path/to/PyVideoTrans", target_lang: "en" },
    video_gen: { engine: "remotion", remotion_project: "video/remotion-app", hyperframes: false },
    distribution: { platforms: ["douyin"], schedule_cron: "0 19 * * *" },
    review: { scrape_comments: true, iterate: true }
  },
  "youtube-default": {
    account: { platform: "youtube", name: "my-youtube", niche: "tech-explainer", style_ref: "config/style/youtube-style.md", target_length_sec: 180, language: "en" },
    topic_mining: { source: "agent_reach", mediacrawler_path: "", keywords: ["trending tech", "how to"], top_n: 15 },
    script_writer: { model: "", de_ai: true, safety_review: true },
    subtitle_dub: { engine: "pyvideotrans", pyvideotrans_path: "/path/to/PyVideoTrans", target_lang: "en" },
    video_gen: { engine: "remotion", remotion_project: "video/remotion-app", hyperframes: true },
    distribution: { platforms: ["youtube"], schedule_cron: "0 10 * * 1,3,5" },
    review: { scrape_comments: true, iterate: true }
  }
};

const SKILLS = [
  { name: "style-replication", title: "风格复刻", desc: "从爆款样本收敛账号人设与脚本口吻，让每账号产出稳定贴人设。" },
  { name: "process-optimization", title: "流程自优化", desc: "用评论/数据反馈自动调整关键词、时长、平台策略，越跑越准。" },
  { name: "safety-review", title: "安全审查", desc: "发布前合规与风控把关：版权、广告法、平台规范、虚假信息。" }
];

const DEAI_RULES = [
  "没有“首先/其次/最后”式教科书结构",
  "没有“在当今社会”“随着……发展”等空泛开头",
  "没有排比三连、没有过度对称句式",
  "没有“值得注意的是”“综上所述”等总结腔",
  "用了至少 1 个具体例子 / 数字 / 人名",
  "有明确主见（敢下判断，不是“各有优劣”）",
  "句子长短交错，有口语停顿感",
  "没有解释显而易见的概念（像对人说话）",
  "结尾有真实互动钩子，不是“感谢观看”",
  "通读一遍：像你本人会说的话吗？"
];

const SAFETY_RULES = [
  "不含违法、暴力、色情、仇恨、诈骗内容",
  "不侵犯他人著作权 / 肖像权 / 商标（素材需授权或自制）",
  "不涉及医疗、金融的违规承诺与硬广",
  "不编造虚假信息 / 不实数据（引用需可核查）",
  "不诱导私下交易、不引流到违规外链",
  "不泄露个人隐私信息",
  "符合平台社区规范与广告法表述要求",
  "政治、社会敏感话题按属地法规审慎处理"
];

// ===== 渲染 =====
function renderPipelineMap() {
  const map = document.getElementById("pipeline-map");
  PIPELINE.steps.forEach((s, i) => {
    const meta = STEP_META[s];
    const el = document.createElement("div");
    el.className = "step";
    el.innerHTML = `${meta.label}<small>${meta.desc}</small>`;
    if (i < PIPELINE.steps.length - 1) {
      const a = document.createElement("span");
      a.className = "arrow";
      a.textContent = "→";
      el.appendChild(a);
    }
    map.appendChild(el);
  });
}

function renderAccounts() {
  const sel = document.getElementById("account-select");
  Object.keys(ACCOUNTS).forEach((k) => {
    const o = document.createElement("option");
    o.value = k;
    o.textContent = `${k}（${ACCOUNTS[k].account.platform} · ${ACCOUNTS[k].account.niche}）`;
    sel.appendChild(o);
  });
}

function renderSkills() {
  const grid = document.getElementById("skills-grid");
  SKILLS.forEach((sk) => {
    const el = document.createElement("div");
    el.className = "skill";
    el.innerHTML = `<h3>${sk.title}</h3><p>${sk.desc}</p>`;
    grid.appendChild(el);
  });
}

function renderLists() {
  const de = document.getElementById("deai-list");
  DEAI_RULES.forEach((r) => { const li = document.createElement("li"); li.textContent = r; de.appendChild(li); });
  const sa = document.getElementById("safety-list");
  SAFETY_RULES.forEach((r) => { const li = document.createElement("li"); li.textContent = r; sa.appendChild(li); });
}

function buildCmd() {
  const acc = document.getElementById("account-select").value;
  const step = document.getElementById("step-select").value;
  const topic = document.getElementById("topic-input").value.trim();
  let cmd = `python3 pipeline/orchestrator.py --account ${acc} --step ${step}`;
  if (step === "script_writing" && topic) cmd += ` --topic "${topic}"`;
  return cmd;
}

function updateCmd() {
  const cmd = buildCmd();
  document.getElementById("cmd-output").textContent = cmd;
  const step = document.getElementById("step-select").value;
  const tip = document.getElementById("run-tip");
  if (step === "all") {
    tip.innerHTML = "将依次跑完 6 步；外部工具未配置时自动降级并产出下一步指引。在本机 <code>ai-media-pipeline/</code> 目录执行。";
  } else if (step === "script_writing") {
    tip.innerHTML = "填“话题”后命令会带上 <code>--topic</code>；产出 script.md + 去AI清单 + 安全审查报告。";
  } else {
    tip.innerHTML = "在本地流水线目录执行该命令即可。";
  }
}

function updateConfig() {
  const acc = document.getElementById("account-select").value;
  document.getElementById("config-view").textContent = JSON.stringify(ACCOUNTS[acc], null, 2);
}

function copyCmd() {
  const btn = document.getElementById("copy-btn");
  navigator.clipboard.writeText(buildCmd()).then(() => {
    btn.textContent = "已复制";
    setTimeout(() => (btn.textContent = "复制"), 1400);
  }).catch(() => {
    btn.textContent = "复制失败";
    setTimeout(() => (btn.textContent = "复制"), 1400);
  });
}

function setEnvBadge() {
  const isLocal = location.protocol === "file:" || location.hostname === "localhost";
  const badge = document.getElementById("env-badge");
  badge.textContent = isLocal ? "本地预览" : location.host;
}

// ===== 一键生成（调后端 API）=====
function getApiBase() {
  const q = new URLSearchParams(location.search).get("api");
  if (q) return q.replace(/\/$/, "");
  return ""; // 同域；线上改为后端 Worker 地址（如 https://ai-media-worker.xxx.workers.dev）
}

function fillGenAccount() {
  const sel = document.getElementById("gen-account");
  Object.keys(ACCOUNTS).forEach((k) => {
    const o = document.createElement("option");
    o.value = k; o.textContent = k;
    sel.appendChild(o);
  });
}

let genTimer = null;
function pollJob(jobId) {
  const base = getApiBase();
  fetch(`${base}/api/job/${jobId}`).then((r) => r.json()).then((j) => {
    const st = document.getElementById("gen-state");
    st.textContent = `状态：${j.status}`;
    st.className = "gen-state " + (j.status || "");
    document.getElementById("gen-log").textContent = j.log_tail || "";
    if (j.status === "done" || j.status === "failed") {
      clearInterval(genTimer);
      document.getElementById("gen-btn").disabled = false;
      const v = document.getElementById("gen-video");
      if (j.videos && j.videos.length) {
        v.innerHTML = `<video src="${base}/api/file?path=${encodeURIComponent(j.videos[0].path)}" controls></video>`;
      } else if (j.status === "done") {
        v.innerHTML = `<p class="hint">流程跑完，但本次无视频产物（视频渲染需后端装好 Remotion/ffmpeg 并开启 RENDER_VIDEO）。可在“账号配置/命令中心”检查各步产出。</p>`;
      }
      return;
    }
  }).catch((e) => {
    document.getElementById("gen-log").textContent = "轮询失败：" + e;
  });
}

function startGenerate() {
  const base = getApiBase();
  const account = document.getElementById("gen-account").value;
  const steps = document.getElementById("gen-steps").value;
  const topic = document.getElementById("gen-topic").value.trim();
  document.getElementById("gen-btn").disabled = true;
  const st = document.getElementById("gen-state");
  st.textContent = "提交中…";
  st.className = "gen-state running";
  document.getElementById("gen-video").innerHTML = "";
  fetch(`${base}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account, steps, topic: topic || null })
  }).then((r) => r.json()).then((d) => {
    if (!d.job_id) throw new Error("未返回 job_id");
    genTimer = setInterval(() => pollJob(d.job_id), 2000);
    pollJob(d.job_id);
  }).catch((e) => {
    st.textContent = "提交失败：" + e.message;
    st.className = "gen-state failed";
    document.getElementById("gen-btn").disabled = false;
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderPipelineMap();
  renderAccounts();
  renderSkills();
  renderLists();
  updateCmd();
  updateConfig();
  setEnvBadge();
  fillGenAccount();
  document.getElementById("gen-btn").addEventListener("click", startGenerate);

  document.getElementById("account-select").addEventListener("change", () => { updateCmd(); updateConfig(); });
  document.getElementById("step-select").addEventListener("change", updateCmd);
  document.getElementById("topic-input").addEventListener("input", updateCmd);
  document.getElementById("copy-btn").addEventListener("click", copyCmd);
});
