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
5. 如果任一环境变量未设置 → **先尝试启动 `wp-post/scripts/wp_post_env.py` GUI 工具**（见下文「启动 GUI 兜底」），让用户在小窗里输入并保存，**不要**回退到对话里直接询问用户输入凭据。
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

### 启动时自检 + GUI 兜底

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

如果三个变量**都**齐了 → 直接往下走（Step 1 上传媒体）。

如果**任意一个**缺失 → **先尝试启动 GUI 兜底工具**（见下一节），不要直接报失败退出。

---

### 启动 GUI 兜底工具（自检失败时）

**目的**：让用户在一个 Tkinter 小窗里填好三个变量并保存，而不是在对话里手输。

**脚本位置**：跟 wp-post 这个 skill 本身放在同一个目录的 `scripts/` 子目录下（按 skill-creator 规范，配套脚本统一归档在 `scripts/` 子目录里）。也就是说：

- `<wp-post 目录>/scripts/wp_post_env.py`

wp-post skill 在用户的本地 mavis 配置里位于 `~/.mavis/skills/wp-post/`。在用户的 manluenSkills 仓库里通常位于：

- `manluenSkills/.claude/skills/wp-post/scripts/wp_post_env.py`（主仓库）
- `manluenSkills-1/.claude/skills/wp-post/scripts/wp_post_env.py`（备份）

AI 不知道确切路径时，按以下顺序探测：

```bash
# macOS / Linux
# SCRIPT_DIR 直接设成 .../wp-post（脚本在 scripts/ 子目录下）
SCRIPT_DIR=""
for p in \
  "$HOME/.mavis/skills/wp-post" \
  "$HOME/Desktop/manluen/manluenSkills/.claude/skills/wp-post" \
  "$HOME/Desktop/manluen/manluenSkills-1/.claude/skills/wp-post"
do
  if [ -f "$p/scripts/wp_post_env.py" ]; then
    SCRIPT_DIR="$p"
    echo "FOUND:$SCRIPT_DIR/scripts/wp_post_env.py"
    break
  fi
done
```

```powershell
# Windows PowerShell
$SCRIPT_DIR = $null
foreach ($p in @(
  "$env:USERPROFILE\.mavis\skills\wp-post",
  "$env:USERPROFILE\Desktop\manluen\manluenSkills\.claude\skills\wp-post",
  "$env:USERPROFILE\Desktop\manluen\manluenSkills-1\.claude\skills\wp-post"
)) {
  if (Test-Path "$p\scripts\wp_post_env.py") {
    $SCRIPT_DIR = $p
    "FOUND:$SCRIPT_DIR\scripts\wp_post_env.py"
    break
  }
}
```

找到路径后，**用图形方式启动 GUI**（不要等子进程返回，因为 Tkinter 窗口会阻塞）。`$SCRIPT_DIR` 是上面探测到的 `.../wp-post` 目录（**不是** `.../wp-post/scripts`）：

```bash
# macOS
open -a Terminal "$SCRIPT_DIR/scripts/wp_post_env.py" 2>/dev/null || python3 "$SCRIPT_DIR/scripts/wp_post_env.py" &
# Linux
xdg-open "$SCRIPT_DIR/scripts/wp_post_env.py" 2>/dev/null || (python3 "$SCRIPT_DIR/scripts/wp_post_env.py" &)
# Windows
start powershell -NoProfile -Command "python '$SCRIPT_DIR\scripts\wp_post_env.py'"
```

如果 `open` / `xdg-open` / `start` 都被沙盒拦了，就 fallback 到直接 `python3 $SCRIPT_DIR/scripts/wp_post_env.py &`（后台跑），然后给用户发提示：

> 「wp-post 的环境变量还没设好，我弹了一个小窗，麻烦填一下保存。
> 填完跟我说一声，我接着跑。」

**AI 在等用户确认期间不要继续往下走**。等用户回「好了」之后 → 跳到下一节「让当前 shell 拿到新值」。

如果完全找不到脚本（用户没装 wp-post 或没把脚本放到上面任何一个位置），才回退到提醒用户去 shell 里 export 三个变量名。

---

### 让当前 shell 拿到新值（GUI 保存之后）

GUI 写完只是把值持久化到了磁盘 rc 文件 / Windows 注册表，**当前 shell 进程的 `os.environ` 还是空的**。
所以 GUI 跑完 + 用户确认后，**AI 必须主动把值加载到当前 shell**：

#### macOS / Linux（自己 source 一下）

```bash
# 默认 shell 是 zsh（macOS 现代默认）
[ -f "$HOME/.zshenv" ] && source "$HOME/.zshenv"
# 如果是 bash（Linux 桌面默认）
[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"
# 如果是 bash 登录 shell
[ -f "$HOME/.bash_profile" ] && source "$HOME/.bash_profile"
[ -f "$HOME/.profile" ] && source "$HOME/.profile"

# 自检
: "${WP_API_USERNAME:?WP_API_USERNAME 未设置}"
: "${WP_APP_PASSWORD:?WP_APP_PASSWORD 未设置}"
: "${WP_SITE_DOMAIN:?WP_SITE_DOMAIN 未设置}"
```

> **关键**：`source` 必须在**当前 mavis 跑的 shell 进程**里执行。`bash -c "source ~/.zshenv"` 那种开子 shell 跑是没用的——子 shell 的环境变量不会回传给父 shell。直接 `source` 即可，mavis 的 shell wrapper 会把 export 同步到后续命令。

#### Windows PowerShell（从注册表读用户级 env，写回当前进程）

```powershell
# 用户级环境变量在 HKEY_CURRENT_USER\Environment 注册表里
# 当前 PowerShell 进程需要重新加载才能拿到
$userEnv = [Environment]::GetEnvironmentVariables("User")
foreach ($name in @("WP_API_USERNAME", "WP_APP_PASSWORD", "WP_SITE_DOMAIN")) {
  if ($userEnv.ContainsKey($name)) {
    Set-Item -Path "Env:$name" -Value $userEnv[$name]
  }
}

# 自检
if (-not $env:WP_API_USERNAME) { throw "WP_API_USERNAME 未设置" }
if (-not $env:WP_APP_PASSWORD) { throw "WP_APP_PASSWORD 未设置" }
if (-not $env:WP_SITE_DOMAIN) { throw "WP_SITE_DOMAIN 未设置" }
```

跑完这一段后，**后续的 curl 命令**（`curl -u "${WP_API_USERNAME}:${WP_APP_PASSWORD}" ...`）就能拿到值了。

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
