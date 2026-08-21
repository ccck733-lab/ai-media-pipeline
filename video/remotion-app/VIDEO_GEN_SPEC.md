# 视频画面生成规格

- 工程: Remotion（react-jsx）
- 画幅: 1080x1920（竖屏，适配抖音/视频号）
- 帧率: 30fps
- 时长: 由 scenes 数 × 每屏帧数决定
- 素材: 把脚本关键句写入 src/Compositions.tsx 的 scenes 数组驱动画面

## 运行
```
cd video/remotion-app
npm install
npm run dev        # 预览
npm run build      # 渲染成片 -> out/video.mp4
```
成片输出到 out/ 后，交给 subtitle_dub 做字幕配音。
