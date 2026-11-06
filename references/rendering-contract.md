# 渲染与标注契约

使用时按节读取：步骤 2 读默认参数/视觉规范；步骤 3–5 读标注/时序/遮罩/配置；步骤 1、4、6、7 读脚本用法。运行前确认当前目录为已验证的 skill 根目录；命令中的 `<PY>` 是探测到的 Python 3 解释器，`<ENV_PY>` 来自环境探测输出，均不可猜测。日常按黑盒调用，首次只读安全的 `--help`，不读源码、不改核心脚本；报错保留日志并停止当前步。

## 默认实现参数

| 项目 | 默认要求 |
|---|---|
| 纸张背景 | 生成图使用暖米黄旧纸色（建议 `#F5EBD7`）；渲染时从原图距四角内缩取样染底，禁止纯白。 |
| 画法 | 每区域 stream 连续笔迹：起笔 `ink`（铺线稿）→ 添彩 `color`（还原原色）；权重 `ink:color = 2:1`。 |
| 笔迹路径 | `--ink-path grid`（网格，默认，稳）或 `skeleton`（骨架追踪，线稿清晰的插画更贴合）。 |
| 上色风格 | `--color-fill contour-wipe`（轮廓扫描，默认）或 `brush`（沿轨迹刷）。 |
| 未绘制区域 | 区域的允许掩码 = 矩形 `region` 扣除「后续区域 + protectedRegions」；未开始区域完全隐藏。 |
| 时长来源 | 每张图的 `sceneDurationMs` 来自该幕字幕的时间跨度（建议 25–35 秒/幕）。 |
| 编辑框 | 预览台默认显示全部编号编辑框；编辑框不属于动画画面内容。 |

## 统一出图视觉规范（强制）

所有场景的源图必须遵循同一套视觉语言；生成前把以下要求完整写入出图提示词，生成后逐条检查：

- **风格与构图：** 极简手绘插图、纯素描草图风格、类似 Notion 的克制涂鸦美学。以概念表达为主，不追求写实；构图简洁、背景干净、大量留白，整体情感平和、清晰，系列内线条/人物/配色一致。
- **颜色与材质：** 米色纸张背景 `#F5EBD7`、深灰色草图线条；仅可用红色、橙色、蓝色 作少量概念性点缀。不得使用其他强调色、高饱和度配色或复杂纹理。
- **人物与对象：** 对象以简洁轮廓、少量线条和留白表达，强调关系/变化/核心概念，而非真实比例、材质与细节。
- **绝对禁止：** 场景源图中的任何文字、词语、字母、数字、字体或标签；写实感、摄影细节、3D 效果、绘画质感；复杂场景、密集背景、繁复装饰和高饱和度画面。
- **绘制手部例外：** 若用户明确说明笔杆上的文字是其标识并要求保留，可保留 `drawing-hand.png` 笔杆上的标识；它不属于场景源图文字，也不需要清除或重绘。未获得用户明确说明时，仍按无文字画面处理。

## 语义排序与像素级标注（必须执行）

1. **阅读依据：** 标注前必须同时具备字幕与已查看的原图。缺任一项先索取，不得生成标注。
2. **顺序依据：** `sequence`、`startMs` 与 `label` 必须反映字幕中的事件先后，而非仅按从左到右、从上到下或视觉显眼程度。
3. **坐标依据：** 每个模块输出原图坐标系的整数像素 `x`、`y`、`width`、`height`；原点左上角，禁止百分比/比例/估算坐标或省略尺寸。`canvas.width`/`canvas.height` 必须等于原图像素尺寸。
4. **模块字段：** 每个元素含 `sequence`、`narrativeRole`、`subtitle`、`region`、`reveal`、`handPath`。`narrativeRole` 用中文说明其在字幕中的叙事作用；`subtitle` 存该区域对应的字幕文本（来自 SRT，供预览台联动与后续用途）；`sequence` 从 1 起连续。
5. **校验：** 生成预览前检查每个区域是否在画布内、是否覆盖对应可见主体、是否与字幕事件相符；重叠主体用 `protectedRegions` 保护后绘制模块。

## 时序模型（stream 画法专用）

- **每幕总时长** `sceneDurationMs` 来自该幕字幕时间跨度（`parse_srt.py` 的 `scenes[].sceneDurationMs`）。
- **区域串行作画：** stream 画法是一支笔在动，同一幕内各区域应**在时间上依次进行**（`startMs` 不重叠）：下一区域从上一区域 `startMs + durationMs`（+ 可选 100–300ms 呼吸）开始。若 `startMs` 重叠，渲染器仍按顺序处理，但视觉上不再是并发。
- **区域内 ink→color：** 每个区域的 `durationMs` 会按 `ink:color = 2:1` 切成起笔段和添彩段。`durationMs` 由预览台的**开始/结束时间**决定（结束−开始），必须将 SRT 的全局时间减去该幕 startMs 后对齐；也可用 150 像素/秒 × 绘制距离作为初始估算。
- **时序校验：** 拖列表只修改数组顺序和 `sequence`，不会自动重排时间；保存后逐项核对数组、`sequence` 与严格递增的 `startMs` 同序、区间串行，最后结束加 500ms 不超过该幕字幕时间预算。预览台可能延长 `sceneDurationMs`，保存后必须和字幕预算复核，超出就停止并返回时序确认；不得静默延长成片。多幕起止和字幕间隙必须列入分镜供用户确认，不得以逐段拼接暗中丢失原时间轴间隙。
- **凝视收尾：** 全部区域画完后自动补到 `sceneDurationMs`，并保证结尾至少停留 0.5 秒完整原图。
- `reveal.direction` 在 stream 画法下**不决定真实笔迹**（笔迹由骨架/网格自动生成），仅供预览台的矩形代理演示；保留它是为了预览台可用。

## 遮罩不变量（编排层，必须执行）

- 在时间 `t`，模块仅可显示其 `reveal.startMs ≤ t` 之后、且不超过当前作画进度的像素；未开始模块的任何线条/填充/图像都不得出现。
- 每个区域的**允许掩码** = 矩形 `region` 扣除全部**后续模块的 `region`**，再扣除本模块 `reveal.protectedRegions`。stream 落墨被限制在允许掩码内，因此后续区域不会提前露线。
- `protectedRegions` 采用与 `region` 相同的原图整数像素坐标，用于矩形过大、主体交叠或背景线条可能泄露的情况。
- 渲染器已实现"限制在允许掩码内落墨 → 后续区域与保护区天然不被触碰"的顺序；预览台矩形代理用等价的 `destination-out` 扣除演示同一编排。

## 配置示例

```json
{
  "sceneId": "scene-01",
  "canvas": { "width": 1672, "height": 941 },
  "storyBasis": "该幕字幕的事件摘要",
  "sceneDurationMs": 9000,
  "elements": [
    {
      "id": "rockery",
      "label": "假山场景",
      "sequence": 1,
      "narrativeRole": "故事的场景铺垫",
      "subtitle": "猴子山上，一只小猴子坐在假山顶端，手里拿着香蕉。",
      "type": "structure",
      "region": { "x": 20, "y": 120, "width": 540, "height": 780 },
      "reveal": { "direction": "top_to_bottom", "startMs": 300, "durationMs": 2600, "maskPaddingPx": 22, "protectedRegions": [] },
      "handPath": { "start": [290, 130], "end": [290, 890], "easing": "easeInOut" }
    }
  ]
}
```

> `direction` / `handPath` 仅供预览台矩形代理使用；成片笔迹由 stream 自动生成，无需精调。

## 使用脚本

所有图像/渲染脚本用 skill 内 `.venv` 的解释器运行（依赖隔离）。先用 `<PY>` 探测环境与解析字幕；本节方括号为可选参数记法，不是 shell 中可原样执行的字符。

1. **准备环境**（首次或缺依赖时）：
   ```bash
   <PY> scripts/prepare_env.py --check   # 探测；成功末行输出 ENV_PY=<路径>，捕获备用
   <PY> scripts/prepare_env.py           # 缺则建 .venv 并装 opencv-python/numpy/av/Pillow
   ```
2. **解析字幕 + 建议分镜**：
   ```bash
   <PY> scripts/parse_srt.py <字幕.srt> --target-sec 30 --min-sec 25 --max-sec 35
   ```
3. **区域编号预览图**（自动探测已有中文字体；探测失败时先定位并确认可用字体，再传 `--font`，不得假设 Windows 字体存在）：
   ```bash
   <ENV_PY> scripts/render_annotation_preview.py <图片> <标注> <预览图输出> [--font <已有中文字体文件>]
   ```
4. **预览台（无需服务器）**：直接用 Chrome / Edge 打开 `assets/preview.html`，点"打开文件夹"选目录 → 载入全部图片+同名标注 → 拖拽编辑 → "保存"写回原文件。写回需 File System Access API（Chrome/Edge）；其它浏览器改为下载后手动覆盖。渲染仍走命令行（下面第 5 步）。
5. **渲染单幕成片**：
   ```bash
   <ENV_PY> scripts/render_stream_whiteboard.py <图片> <标注> <输出mp4> --bare-tip \
       [--ink-path grid|skeleton] [--color-fill contour-wipe|brush] [--total-ms <毫秒>]
   ```
   `--total-ms` 缺省时用标注里的 `sceneDurationMs`。末行输出 `OUTPUT=<路径>`，以该路径为实际交付，不假设转码必成功。默认不叠加带文字的手部；仅在用户明确确认标识归属/授权并要求保留时，传入已核实的手部 PNG 位置参数，同时去掉 `--bare-tip`。输出只有画面，不自动合成音轨。
6. **多幕合并**：
   ```bash
   <ENV_PY> scripts/merge_scenes.py --inputs 幕1.mp4 幕2.mp4 幕3.mp4 --output final.mp4
   ```
