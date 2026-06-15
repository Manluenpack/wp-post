---
name: wp-post
description: WordPress 文章发布工具，用于上传 HTML 文章内容到 WordPress 站点。触发条件：(1) 用户请求发布文章、上传文章到网站、写文章到WordPress (2) 用户提到文章插图、配图、需要上传图片 (3) 用户要求生成文章摘要。功能：媒体文件上传、文章创建发布、HTML 内容插入图片。所有凭据（用户名、应用密码、站点域名）必须从环境变量读取，禁止在对话/prompt 中明文出现。
---

# WP-Post

## 安全约束（最高优先级）

**所有 WordPress 凭据必须从环境变量读取，禁止让模型读取、记录或询问用户输入。**

### 必需的环境变量

| 变量名 | 含义 | 示例 |
|--------|------|------|
| `WP_API_USERNAME` | WordPress 用户名（应用密码所属账号） | （不在文档中写出实际值） |
| `WP_APP_PASSWORD` | WordPress 应用密码（Application Password） | （不在文档中写出实际值） |
| `WP_SITE_DOMAIN` | 站点域名（不含协议头） | `www.example.com` |

### 硬性规则

1. **禁止**在 prompt、对话、JSON 文件、命令历史中明文出现 `WP_APP_PASSWORD` 的值。
2. **禁止**询问用户「你的应用密码是什么」「你的用户名是什么」「你的站点域名是啥」。
3. **禁止**把凭据写进 `post-data.json` 或任何中间文件。
4. **禁止**用 `-u "user:pass"` 的形式拼出明文凭据；必须通过 shell 自身的环境变量展开机制读取。
5. 如果任一环境变量未设置 → **立即报错退出**，**只允许**提醒用户去 shell 里 export 对应变量名，**不要**回退到询问用户、不要读取或回显变量值。
6. 错误提示中只能写「环境变量 XXX 未设置」，**不能**透露变量的值；提醒用户时也**只能说变量名**。

### 跨平台 shell 说明

mavis 在 macOS / Linux 下默认使用 zsh / bash（POSIX 风格），在 Windows 下默认使用 **PowerShell**。**两边的环境变量语法不同**，必须按平台选择对应写法：

| 平台 | 默认 shell | 环境变量访问 | 设置方式 |
|------|-----------|-------------|---------|
| macOS / Linux | zsh / bash | `${VAR}` 或 `$VAR` | `export VAR=value` |
| Windows (PowerShell) | powershell | `$env:VAR` | `$env:VAR = "value"` |
| Windows (Git Bash / WSL) | bash | `${VAR}` 或 `$VAR` | `export VAR=value` |
| Windows (cmd，**不推荐**) | cmd | `%VAR%` | `set VAR=value` |

> **mavis 在 Windows 上跑命令时默认走 PowerShell**，所以 Windows 用户应当用 `$env:VAR` 而不是 `${VAR}`。下面的 curl 模板分两种写法给出。

### 在 curl 中读取环境变量

#### macOS / Linux / Git Bash / WSL（bash 风格）

```bash
# 媒体上传
curl -u "${WP_API_USERNAME}:${WP_APP_PASSWORD}" \
  -X POST -H "Content-Type: image/webp" \
  -H "Content-Disposition: attachment; filename=\"文件名.webp\"" \
  --data-binary @/path/to/image.webp \
  "https://${WP_SITE_DOMAIN}/wp-json/wp/v2/media"

# 文章上传
curl -u "${WP_API_USERNAME}:${WP_APP_PASSWORD}" \
  -X POST -H "Content-Type: application/json" \
  --data-binary @/path/to/post-data.json \
  "https://${WP_SITE_DOMAIN}/wp-json/wp/v2/posts"

# 删除文章
curl -u "${WP_API_USERNAME}:${WP_APP_PASSWORD}" \
  -X DELETE \
  "https://${WP_SITE_DOMAIN}/wp-json/wp/v2/posts/文章ID"
```

#### Windows PowerShell

```powershell
# 媒体上传
curl -u "$($env:WP_API_USERNAME):$($env:WP_APP_PASSWORD)" `
  -X POST -H "Content-Type: image/webp" `
  -H "Content-Disposition: attachment; filename=`"文件名.webp`"" `
  --data-binary @C:/path/to/image.webp `
  "https://$env:WP_SITE_DOMAIN/wp-json/wp/v2/media"

# 文章上传
curl -u "$($env:WP_API_USERNAME):$($env:WP_APP_PASSWORD)" `
  -X POST -H "Content-Type: application/json" `
  --data-binary @C:/path/to/post-data.json `
  "https://$env:WP_SITE_DOMAIN/wp-json/wp/v2/posts"

# 删除文章
curl -u "$($env:WP_API_USERNAME):$($env:WP_APP_PASSWORD)" `
  -X DELETE `
  "https://$env:WP_SITE_DOMAIN/wp-json/wp/v2/posts/文章ID"
```

> PowerShell 里 `$env:VAR` 在双引号字符串中可以直接插值，但**用于 `-u` 这种位置时仍要用 `"$($env:VAR):$($env:VAR)"` 子表达式**包起来，否则 `-u` 接收到的会是字面量 `$env:VAR`。PowerShell 的反引号 ``` ` ``` 是续行符（不是 bash 的反斜杠 `\`）。

### 启动时自检

执行任何 wp-post 工作流之前，先按当前平台跑对应的自检。

#### macOS / Linux / Git Bash / WSL

```bash
: "${WP_API_USERNAME:?WP_API_USERNAME 未设置}"
: "${WP_APP_PASSWORD:?WP_APP_PASSWORD 未设置}"
: "${WP_SITE_DOMAIN:?WP_SITE_DOMAIN 未设置}"
```

#### Windows PowerShell

```powershell
if (-not $env:WP_API_USERNAME) { throw "WP_API_USERNAME 未设置" }
if (-not $env:WP_APP_PASSWORD) { throw "WP_APP_PASSWORD 未设置" }
if (-not $env:WP_SITE_DOMAIN) { throw "WP_SITE_DOMAIN 未设置" }
```

任意一行失败就停止，**不要**回退到询问用户，也不要读取/记录/显示变量的值。

**此时唯一允许的动作是提醒用户去 shell 里 export 对应的变量**，比如向用户输出：

> 「wp-post 需要的环境变量还没设好，请在终端里 export 一下：
> `WP_API_USERNAME`、`WP_APP_PASSWORD`、`WP_SITE_DOMAIN`
> 设好后再让我继续。」

提醒时**只说变量名**，不要说「把你刚才那个密码给我」「你的用户名是啥」，更不要把 shell 里读到的值回显到对话里。

---

## 快速开始

使用 curl 命令完成 WordPress 文章发布：

### 1. 上传媒体（文章插图）

```bash
curl -u "${WP_API_USERNAME}:${WP_APP_PASSWORD}" \
  -X POST -H "Content-Type: image/webp" \
  -H "Content-Disposition: attachment; filename=\"文件名.webp\"" \
  --data-binary @/path/to/image.webp \
  "https://${WP_SITE_DOMAIN}/wp-json/wp/v2/media"
```

- **返回数据**包含 `id`（媒体ID）、`source_url`（图片URL）等字段
- 记录第一张图片的 `id` 作为封面图 `featured_media`

### 2. 上传文章

由于文章内容可能较长，建议使用 JSON 文件方式上传：

**Step 2.1: 创建 post-data.json 文件（文件位置：`content/文章标题/post-data.json`）**

```json
{
  "title": "文章标题",
  "content": "<h2>标题</h2><p>内容...</p>",
  "excerpt": "摘要（150字符以内）",
  "status": "draft",
  "categories": [categories-id],
  "featured_media": 封面图媒体ID
}
```

**Step 2.2: 上传文章**

```bash
curl -u "${WP_API_USERNAME}:${WP_APP_PASSWORD}" \
  -X POST -H "Content-Type: application/json" \
  --data-binary @/path/to/post-data.json \
  "https://${WP_SITE_DOMAIN}/wp-json/wp/v2/posts"
```

**注意**：
- `--data-binary` 参数可以避免 shell 转义问题
- JSON 文件路径使用绝对路径
- 避免使用 `-d` 参数直接传 JSON，使用 `--data-binary @文件路径` 方式

## 工作流程

### Step 0: 凭据自检（每次会话开始时执行一次）

执行上面的「启动时自检」代码段。任何一个变量缺失就停止，不要往下走。

### Step 1: 上传所有插图

1. 遍历 `content/文章标题/generated-images/` 文件夹下的所有图片文件（.webp格式）
2. 依次调用媒体上传 API，记录每张图片的返回数据
3. 保存第一张图片的媒体 ID 用于封面

### Step 2: 插入图片到 HTML

1. 分析 HTML 内容，找到合适的 `<h2>` 段落
2. 根据图片文件名确定相关内容，在 `<h2>` 后的适当位置插入
3. 使用格式：`<img src="图片URL" alt="描述" width="宽度" height="高度">`，必须选择生成的图片不可以使用参考图片的 URL

### Step 3: 生成摘要

1. 从 HTML 内容中提取文本（去除 HTML 标签）
2. 截取前 150 字符（包括空格）作为摘要

### Step 4: 文章草稿

1. 组装 JSON 请求体（**不包含任何凭据**）
2. 调用文章上传 API
3. 返回草稿结果（文章 ID 和链接）

### Step 5: 检查并清理重复文章

1. 发布后检查是否出现重复（同一标题出现多篇）
2. 如果发现重复，保留 ID 较小的那篇，删除 ID 较大的那篇
3. 删除命令：

```bash
curl -u "${WP_API_USERNAME}:${WP_APP_PASSWORD}" \
  -X DELETE \
  "https://${WP_SITE_DOMAIN}/wp-json/wp/v2/posts/文章ID"
```

## API 端点

| 操作 | 端点 | Content-Type |
|------|------|--------------|
| 媒体上传 | `https://${WP_SITE_DOMAIN}/wp-json/wp/v2/media` | `image/*` |
| 文章上传 | `https://${WP_SITE_DOMAIN}/wp-json/wp/v2/posts` | `application/json` |
| 删除文章 | `https://${WP_SITE_DOMAIN}/wp-json/wp/v2/posts/{id}` | （DELETE） |

## 认证信息

**必须通过环境变量提供**：`WP_API_USERNAME`、`WP_APP_PASSWORD`、`WP_SITE_DOMAIN`。

设置示例（用户在本地 shell 执行，不要贴到对话里）：

#### macOS / Linux / Git Bash / WSL

```bash
export WP_API_USERNAME="..."
export WP_APP_PASSWORD="..."
export WP_SITE_DOMAIN="www.example.com"
```

#### Windows PowerShell

```powershell
$env:WP_API_USERNAME = "..."
$env:WP_APP_PASSWORD = "..."
$env:WP_SITE_DOMAIN = "www.example.com"
```

> PowerShell 的 `$env:VAR = "value"` 只对**当前会话**生效；想持久化用 `[Environment]::SetEnvironmentVariable("WP_API_USERNAME", "...", "User")`。

## HTML 内容格式要求

在将 markdown 转换为 HTML 上传到 WordPress 时，必须遵循以下格式规范：

### HTML 格式规范

**IMPORTANT**: 文章内容必须转换为 HTML 格式，但禁止使用任何内联样式。

**正确的格式：**
```html
<h2>Introduction</h2>
<p>This is a paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
<ul>
<li>List item one</li>
<li>List item two</li>
</ul>
<table>
<thead>
<tr><th>Column 1</th><th>Column 2</th></tr>
</thead>
<tbody>
<tr><td>Data 1</td><td>Data 2</td></tr>
</tbody>
</table>
```

**禁止的格式：**
- 内联样式：`<p style="color: red;">` ❌
- CSS 类：`<p class="highlight">` ❌
- style 标签：`<style>...</style>` ❌

**允许的 HTML 标签（链接仅允许 href 属性）：**
- 标题：`<h2>`, `<h3>`
- 段落：`<p>`
- 列表：`<ul>`, `<ol>`, `<li>`
- 强调：`<strong>`, `<em>`
- 链接：`<a href="...">`
- 表格：`<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>`
- 分隔线：`<hr />`

### Markdown 转 HTML 对照表

| Markdown 语法 | HTML 输出 |
|---------------|-----------|
| `## Heading` | `<h2>Heading</h2>` |
| `### Heading` | `<h3>Heading</h3>` |
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `- item` | `<li>item</li>` (外层需包裹 `<ul>` 或 `<ol>`) |
| `[text](url)` | `<a href="url">text</a>` |
| `---` | `<hr />` |
| `\| th \| th \|`<br>`\| td \| td \|` | `<table>` 结构 |

### 完整 HTML 文章结构示例

```html
<h2>Introduction</h2>

<p>As a restaurant owner, selecting the right food packaging can significantly impact your operations...</p>

<h2>Why Bento Boxes Matter</h2>

<p>A well-designed bento box does more than just hold food:</p>

<ul>
<li><strong>Enhances presentation</strong> – Multiple compartments keep dishes separated</li>
<li><strong>Maintains quality</strong> – Proper design prevents flavor mixing</li>
</ul>

<h2>Key Factors to Consider</h2>

<h3>1. Material Quality</h3>

<p>The material determines durability and food safety:</p>

<table>
<thead>
<tr><th>Material</th><th>Heat Resistance</th><th>Best For</th></tr>
</thead>
<tbody>
<tr><td>PP</td><td>Up to 100°C</td><td>Hot food applications</td></tr>
</tbody>
</table>

<hr />

<p><em>This guide is part of our commitment to helping food service professionals.</em></p>
```