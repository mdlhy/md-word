# MD→WPS 一键排版

将 AI 生成的 Markdown 文件一键转换为 WPS 友好的 .docx 文件。公式、表格、标题、列表、引用、代码块、图片全部搞定。

## 解决什么问题

AI 生成的 Markdown 粘贴到 WPS 后：
- 公式变成乱码
- 表格错乱
- 标题没有层级样式
- 列表嵌套丢失
- 引用块没有样式
- 代码块没有底色
- 图片链接失效

本工具一键全部修好。

## 功能

### Markdown → docx
- 上传 .md 文件，生成格式完整的 .docx
- 公式 `$...$` / `$$...$$` → WPS 可编辑的 OMML 格式（失败保留 LaTeX 原文）
- 表格 → Word 原生表格（支持三线表）
- 标题 → Heading 1-3 样式
- 有序/无序列表 → 多级 Word 列表
- 引用块 → 缩进 + 左边框
- 代码块 → Consolas 字体 + 灰色背景
- 远程图片自动下载嵌入，SVG/WebP 自动转 PNG

### docx 修复
- 上传已有 .docx，自动检测并修复格式问题
- 修复标题样式（去掉 # 号）
- 修复列表样式
- 修复表格宽度/边框
- 修复公式为 OMML

### 样式模板
- 学术论文：宋体/Times，1.5 倍行距
- 课程作业：黑体/宋体，单倍行距
- 工作文档：微软雅黑，1.25 倍行距

### WPS 兼容检测
- 转换后显示每个元素的风险等级（🟢低 / 🟡中 / 🔴高）
- 高风险公式（如 `\begin{aligned}`）提前预警

## 安装

```bash
git clone https://github.com/mdlhy/md-formula-converter.git
cd md-formula-converter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

macOS 额外依赖（SVG 支持）：
```bash
brew install cairo pango
```

## 使用

**双击 `start.command`** 启动，浏览器自动打开 http://localhost:8972

或手动启动：
```bash
source venv/bin/activate
python app.py
```

## 技术栈

- **后端**: Python + FastAPI
- **MD 解析**: mistune v3（自定义数学公式插件）
- **公式转换**: math2docx → OMML
- **docx 生成**: python-docx + lxml（三线表边框操控）
- **图片处理**: cairosvg / svglib+reportlab（SVG→PNG）、Pillow（WebP→PNG）
- **前端**: 原生 HTML/CSS/JS，零框架

## License

MIT
