---
name: wp-post
description: WordPress 文章发布工具，用于上传 HTML 文章内容到 WordPress 站点。触发条件：(1) 用户请求发布文章、上传文章到网站、写文章到WordPress (2) 用户提到文章插图、配图、需要上传图片 (3) 用户要求生成文章摘要。功能：媒体文件上传、文章创建发布、HTML 内容插入图片。
---

# WP-Post

## 快速开始

使用 curl 命令完成 WordPress 文章发布：

### 1. 上传媒体（文章插图）

```bash
curl -u "[api-username]:[app-password]" \
  -X POST -H "Content-Type: image/webp" \
  -H "Content-Disposition: attachment; filename=\"文件名.webp\"" \
  --data-binary @/path/to/image.webp \
  "https://[域名]/wp-json/wp/v2/media"
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
curl -u "[api-username]:[app-password]" \
  -X POST -H "Content-Type: application/json" \
  --data-binary @/path/to/post-data.json \
  "https://[域名]/wp-json/wp/v2/posts"
```

**注意**：
- `--data-binary` 参数可以避免 shell 转义问题
- JSON 文件路径使用绝对路径
- 避免使用 `-d` 参数直接传 JSON，使用 `--data-binary @文件路径` 方式

## 工作流程

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

1. 组装 JSON 请求体
2. 调用文章上传 API
3. 返回草稿结果（文章 ID 和链接）

### Step 5: 检查并清理重复文章

1. 发布后检查是否出现重复（同一标题出现多篇）
2. 如果发现重复，保留 ID 较小的那篇，删除 ID 较大的那篇
3. 删除命令：
```bash
curl -u "[api-username]:[app-password]" \
  -X DELETE \
  "https://[域名]/wp-json/wp/v2/posts/文章ID"
```

## API 端点

| 操作 | 端点 | Content-Type |
|------|------|--------------|
| 媒体上传 | `https://www.manluenpack.com/wp-json/wp/v2/media` | `image/*` |
| 文章上传 | `https://www.manluenpack.com/wp-json/wp/v2/posts` | `application/json` |

## 认证信息
位于AGENT配置文件中

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
