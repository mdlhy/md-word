# 更新日志

## 2026-04-29 v2.1 — 外部 AI 修改记录

### 后端改动

| 文件 | 改动 |
|------|------|
| `app.py` | 公式详情 API 返回新增 `page` 字段（公式所在页码） |
| `converter/models.py` | `FormulaDetail` 新增 `page: int \| None` 字段 |
| `converter/orchestrator.py` | 1. 新增页码追踪逻辑：遍历段落时计算 `current_page`，传递给 `replace_formulas_in_paragraph`；2. 删除 `convert_docx()` 中重复遍历+二次 save 的 bug（之前公式会被处理两遍） |
| `converter/replacer.py` | `replace_formulas_in_paragraph` 新增 `page` 参数，写入 `FormulaDetail.page` |
| `converter/docx_repair.py` | 标题修复时强制 `run.font.color.rgb = RGBColor(0, 0, 0)`（避免继承模板超链接颜色） |
| `converter/elements/heading.py` | 同上，MD 转换时标题也强制黑色 |

### 前端改动

| 文件 | 改动 |
|------|------|
| `web/index.html` | 1. 文件信息新增 `file-meta`（文件大小等元信息）和 `process-summary`（处理说明）；2. 按钮文案"开始转换"→"开始处理"；3. 结果页新增标题区 `result-title`/`result-meta`；4. stats 区域移入 HTML 结构（之前在 JS 中动态生成）；5. 兼容面板新增"展开详情"按钮；6. 公式列表包裹在 `formula-panel` 中（可整体隐藏） |
| `web/app.js` | 1. 全局重构：DOM 引用集中为 `els` 对象，状态集中为 `state` 对象；2. 新增 `workflows` 配置（md/repair/convert 三种流程的定义）；3. 新增 `selectFile`/`submitCurrentFile`/`updateProcessUI` 等函数；4. 兼容面板默认折叠，点击"展开详情"展开；5. 公式列表仅在 v1 convert 模式下显示；6. 下载文件名根据 workflow 自动命名 |
| `web/style.css` | 1. 配色从蓝色系改为绿色系（`--color-primary: #0f766e`）；2. 标题栏从渐变蓝色改为白色磨砂效果（`backdrop-filter: blur`）；3. 内容最大宽度从 800px 扩到 1040px；4. 上传区域样式更精致（图标带背景框、hover 阴影）；5. 新增 `result-header`/`result-title`/`result-meta`/`compat-header`/`process-summary` 等样式；6. 整体视觉更接近 Notion/Linear 风格 |

### 无关文件（待清理）

- `node_modules/` — 生成产品改进建议 .docx 时临时安装的 npm 依赖
- `package.json` / `package-lock.json` — 同上
- `generate_report.js` — 生成产品改进建议 .docx 的 Node.js 脚本
- `产品改进建议.md` / `MD_to_WPS_产品改进建议.docx` — 产品文档，不属于项目代码
