# MD / Word 格式助手

一个面向 WPS / Word 的本地文档格式助手。

项目现在的主线是 **Pandoc + Python 后处理**：先用 Pandoc 生成结构稳定的 `.docx`，再用 Python 修复 WPS 兼容细节、公式、表格、标题、图片和常见中文排版规则。没有安装 Pandoc 时，`auto` 模式会回退到 legacy 转换链路。

## 主要能力

- Markdown 转 Word：上传 `.md`，生成 WPS 友好的 `.docx`。
- Word 格式自适应：上传 `.docx`，按模板和自定义规则修复格式。
- 公式处理：支持 `$...$`、`$$...$$`，尽量转换为 Word/WPS 可编辑公式。
- 快捷粘贴：把含 `$` 的 LaTeX 文本转换为更适合 WPS 公式粘贴的代码格式，并自动删除公式定界符。
- 格式预设：内置论文常用、办公清爽、紧凑打印、跟随模板，也支持自定义字体、字号、行距、缩进、页边距、标题编号、三线表和页码。
- 代码块：使用 Pygments 做语法高亮。
- 图表块：支持矩阵、柱状图、折线图、饼图、散点图、网络图和流程图渲染。
- 图片处理：本地图片优先；远程图片默认关闭，可通过环境变量开启。
- 兼容性报告：转换后返回 WPS 风险提示和公式统计。
- CLI 批处理：支持单文件、目录批量和递归转换。

## 快速开始

```bash
git clone https://github.com/mdlhy/md-word.git
cd md-word

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

推荐安装 Pandoc：

```bash
brew install pandoc
python -m converter.cli --check-runtime
```

启动网页端：

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8972
```

浏览器打开：

```text
http://127.0.0.1:8972/
```

macOS 也可以在安装好依赖后双击：

```text
start.command
```

Linux 可运行：

```bash
./start.sh
```

## 使用方式

### Web UI

首页是统一入口：

- 左侧主面板：`MD / Word 格式助手`
- 右侧侧栏：`快捷粘贴`
- 上传 `.md`：执行 Markdown 转 Word
- 上传 `.docx`：执行 Word 格式自适应

格式区默认显示常用预设，更多细节放在“更多自定义”里。

### CLI

单文件转换：

```bash
python -m converter.cli input.md
```

指定输出文件：

```bash
python -m converter.cli input.md -o output.docx
```

指定模板：

```bash
python -m converter.cli input.md -t academic
python -m converter.cli input.md -t report
python -m converter.cli input.md -t dialectics
```

指定引擎：

```bash
python -m converter.cli input.md --engine auto
python -m converter.cli input.md --engine pandoc
python -m converter.cli input.md --engine legacy
```

批量转换目录：

```bash
python -m converter.cli ./docs -o ./output
python -m converter.cli ./docs -o ./output -r
```

其他常用命令：

```bash
python -m converter.cli --list-templates
python -m converter.cli --check-runtime
python -m converter.cli input.md --three-line
python -m converter.cli input.md -v
```

## 模板与格式预设

文档模板：

| 模板 ID | 名称 | 典型用途 |
| --- | --- | --- |
| `academic` | 学术论文 | 宋体 / Times New Roman，小四，1.5 倍行距，论文页边距 |
| `report` | 工作文档 | 更适合报告、说明文档和办公材料 |
| `dialectics` | 自然辩证法论文 | 面向自然辩证法课程论文格式 |

网页格式预设：

| 预设 | 说明 |
| --- | --- |
| 论文常用 | 宋体小四、1.5 倍行距、三线表 |
| 办公清爽 | 微软雅黑、1.25 倍行距、标准页边距 |
| 紧凑打印 | 五号字、1.15 倍行距、窄页边距 |
| 跟随模板 | 不覆盖模板样式，只使用所选参考模板 |

## Markdown 扩展

### 公式

```markdown
行内公式：$E=mc^2$

块级公式：
$$
\frac{a}{b}
$$
```

### 代码块

````markdown
```python
def hello():
    print("Hello")
```
````

### 图表块

矩阵：

````markdown
```matrix
name: A
1 2 3
4 5 6
7 8 9
caption: 矩阵 A
```
````

柱状图：

````markdown
```chart
type: bar
title: 性能对比
labels: 冒泡排序, 快速排序, 归并排序
时间(ms): 450, 35, 38
caption: 排序算法性能对比
```
````

流程图：

````markdown
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

## API

本地服务默认运行在 `http://127.0.0.1:8972`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/convert-md` | Markdown 转 `.docx` |
| `POST` | `/api/repair` | `.docx` 格式自适应修复 |
| `POST` | `/api/paste-wps` | 快捷粘贴公式转换 |
| `GET` | `/api/download/{download_id}` | 下载转换结果 |
| `GET` | `/api/templates` | 查看文档模板 |
| `GET` | `/api/format-presets` | 查看网页格式预设 |
| `GET` | `/api/runtime` | 检查 Pandoc、参考模板和远程图片策略 |

限制：

- 上传文件最大 `50MB`。
- 快捷粘贴文本最大 `2MB`。
- 下载文件默认保留 `30` 分钟。

## 运行环境

基础依赖：

- Python 3.10+
- FastAPI / Uvicorn
- python-docx / lxml
- mistune
- math2docx / latex2mathml
- Pygments
- matplotlib / networkx
- Pillow / cairosvg / svglib / reportlab

推荐外部依赖：

- Pandoc：Markdown 转 Word 主引擎。
- macOS SVG 支持依赖：

```bash
brew install cairo pango
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MD2WPS_ENGINE` | `auto` | CLI 默认引擎，可设为 `auto`、`pandoc`、`legacy` |
| `MD2WPS_ALLOWED_ORIGINS` | `http://127.0.0.1:8972,http://localhost:8972` | CORS 白名单 |
| `MD2WPS_ALLOW_REMOTE_IMAGES` | 空 | 设为 `1`、`true` 或 `yes` 后允许处理远程图片 |

## 开发与测试

运行全量测试：

```bash
venv/bin/python -m pytest -q
```

常用检查：

```bash
python -m converter.cli --check-runtime
node --check web/app.js
```

当前重构版本的基线：

```text
70 passed
```

## 项目结构

```text
app.py                     FastAPI 服务和 API
converter/                 转换、修复、Pandoc、公式、样式和图片处理
templates/                 Word 参考模板
web/                       原生 HTML/CSS/JS 前端
tests/                     回归测试
start.command              macOS 启动脚本
start.sh                   Linux 启动脚本
start.bat                  Windows 启动脚本
```

## 设计取向

这个项目不是单纯的 Markdown 转换器，而是一个面向中文 WPS/Word 使用场景的格式助手。优先保证：

- WPS 打开后格式稳定。
- 中文论文和办公文档排版足够可控。
- 公式、表格、标题、图片和代码块有可回归测试。
- Pandoc 负责结构转换，Python 负责最后一公里的格式修复。

## License

MIT
