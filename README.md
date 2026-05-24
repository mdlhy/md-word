# MD / Word 格式助手

面向 WPS / Word 的本地格式助手，覆盖两个主流程：

1. Markdown 转 Word：将 AI 生成的 Markdown 转成 WPS 友好的 `.docx`。
2. Word 格式自适应：上传已有 `.docx`，自动修复标题、列表、表格、公式和正文格式。

网页端支持自定义常见排版规则，包括中文/英文字体、字号、行距、首行缩进、段落对齐、页边距、标题编号、三线表和页码。

## 解决什么问题

AI 生成的 Markdown 粘贴到 WPS 后：
- 公式变成乱码
- 表格错乱
- 标题没有层级样式
- 列表嵌套丢失
- 引用块没有样式
- 代码块没有底色
- 图片链接失效

本工具提供转换、修复和格式自定义三件事。

## 功能

### Markdown → docx
- 上传 .md 文件，生成格式完整的 .docx
- 公式 `$...$` / `$$...$$` → WPS 可编辑的 OMML 格式（失败保留 LaTeX 原文）
- 表格 → Word 原生表格（支持三线表）
- 标题 → Heading 1-3 样式
- 有序/无序列表 → 多级 Word 列表
- 引用块 → 缩进 + 左边框
- **代码块 → 语法高亮（30+ 语言，VS Code 风格主题）**
- 远程图片自动下载嵌入，SVG/WebP 自动转 PNG
- **图表渲染 → 矩阵/柱状图/折线图/饼图/网络图/流程图**
- 支持网页端自定义格式设置，并将同一套规则应用到 Pandoc 后处理

### docx 修复
- 上传已有 .docx，自动检测并修复格式问题
- 修复标题样式（去掉 # 号）
- 修复列表样式
- 修复表格宽度/边框
- 修复公式为 OMML
- 支持按网页端格式规则自适应调整正文、页边距、表格和标题编号

### 样式模板
- 学术论文：宋体/Times，1.5 倍行距
- 工作文档：微软雅黑，1.25 倍行距
- 自然辩证法论文：方正小标宋/仿宋，22磅行距

### WPS 兼容检测
- 转换后显示每个元素的风险等级（🟢低 / 🟡中 / 🔴高）
- 高风险公式（如 `\begin{aligned}`）提前预警

### 命令行工具
- 支持单文件和目录批量转换
- 可选模板和三线表样式
- 递归处理子目录

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

推荐安装 Pandoc 作为 Markdown→docx 主引擎：
```bash
brew install pandoc
python -m converter.cli --check-runtime
```

未安装 Pandoc 时，默认 `auto` 模式会回退到 legacy 转换链路；安装后会自动优先使用 Pandoc + Python 后处理。

## 使用

### Web UI

**双击 `start.command`** 启动，浏览器自动打开 http://localhost:8972

或手动启动：
```bash
source venv/bin/activate
python app.py
```

### 命令行

```bash
# 单文件转换
python -m converter.cli input.md

# 指定输出路径
python -m converter.cli input.md -o output.docx

# 使用指定模板
python -m converter.cli input.md -t report

# 使用三线表
python -m converter.cli input.md --three-line

# 批量转换目录
python -m converter.cli ./docs/ -o ./output/

# 递归处理子目录
python -m converter.cli ./docs/ -o ./output/ -r

# 列出所有模板
python -m converter.cli --list-templates

# 详细日志
python -m converter.cli input.md -v

# 检查 Pandoc 运行环境
python -m converter.cli --check-runtime

# 指定转换引擎
python -m converter.cli input.md --engine pandoc
python -m converter.cli input.md --engine legacy
```

### 代码语法高亮

代码块自动应用语法高亮，支持 30+ 种语言：

```python
def hello():
    print("Hello, World!")
```

```javascript
function hello() {
    console.log("Hello, World!");
}
```

### 图表渲染

使用特殊代码块创建图表：

````markdown
```matrix
name: A
1 2 3
4 5 6
7 8 9
caption: 矩阵 A
```

```chart
type: bar
title: 性能对比
labels: 冒泡排序, 快速排序, 归并排序
时间(ms): 450, 35, 38
caption: 排序算法性能对比
```

```workflow
title: 登录流程
[开始]
(输入用户名密码)
{验证凭据}
(授权访问)
[结束]
caption: 用户登录流程图
```
````

| 图表类型 | 说明 | 依赖 |
|:---------|:-----|:-----|
| `matrix` | 矩阵图 | matplotlib |
| `chart` | 柱状/折线/饼/散点图 | matplotlib |
| `graph` | 网络/有向图 | matplotlib + networkx |
| `workflow` | 流程图 | matplotlib |

## 技术栈

- **后端**: Python + FastAPI
- **MD 解析**: mistune v3（自定义数学公式插件）
- **Pandoc 主线**: Pandoc docx/reference.docx + Python 后处理（auto 模式优先）
- **公式转换**: math2docx → OMML（备选：latex2mathml → MathML → OMML）
- **代码高亮**: Pygments（30+ 语言，VS Code 主题）
- **图表渲染**: matplotlib + networkx
- **docx 生成**: python-docx + lxml（三线表边框操控）
- **图片处理**: cairosvg / svglib+reportlab（SVG→PNG）、Pillow（WebP→PNG）
- **前端**: 原生 HTML/CSS/JS，零框架

## License

MIT
