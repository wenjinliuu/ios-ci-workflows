# 腾讯云开发 CloudBase 接入指南

中央仓库里和 CloudBase 相关的全部内容都在这里：AI 通过 **官方 MCP** 操作后端、用 **CloudBase CLI** 自动部署、以及把两者接到 GitHub Actions 的可复用工作流。

| 组件 | 位置 | 作用 |
| --- | --- | --- |
| CloudBase MCP 网关 | [`cloudbase-mcp-gateway/`](../cloudbase-mcp-gateway/) | Cloudflare Worker：GitHub 登录 → 官方 Hosted MCP，让手机上的 ChatGPT / Claude 等远程 MCP 客户端安全连接 |
| 网关部署工作流 | [`.github/workflows/cloudbase-mcp-gateway-deploy.yml`](../.github/workflows/cloudbase-mcp-gateway-deploy.yml) | 可复用：类型检查 → 写入 Worker Secrets → 部署 → 公网自检 |
| CLI 部署工作流 | [`.github/workflows/cloudbase-deploy.yml`](../.github/workflows/cloudbase-deploy.yml) | 可复用：用环境 API Key 登录 `tcb`，部署云函数 / 静态托管 |
| 网关代码检查 | [`.github/workflows/cloudbase-mcp-gateway.yml`](../.github/workflows/cloudbase-mcp-gateway.yml) | 修改网关代码时自动类型检查、lint、打包 |

## 1. 一把钥匙：环境 API Key

云开发控制台 → 你的环境 → **API Key 管理** → 新建。这一个 Key 同时用于：

- MCP 网关换取官方 Hosted MCP token（Worker Secret `CLOUDBASE_API_KEY`）
- CLI 登录：`tcb login --cloudbase-api-key <key> -e <envId>`（Actions Secret `CLOUDBASE_API_KEY`）

建议网关和 CI 各建一个 Key，方便单独吊销。另一种凭据是腾讯云 CAM 的 SecretId / SecretKey（整个腾讯云账号级别，权限更大），只在需要时使用。

## 2. 让 AI 操作后端：官方 MCP 的三种接法

官方 MCP 服务：[`@cloudbase/cloudbase-mcp`](https://github.com/TencentCloudBase/CloudBase-AI-Toolkit)（MIT）。国内站端点 `https://tcb-api.cloud.tencent.com/mcp/v1`，国际站 `https://tcb-api.tencentcloud.com/mcp/v1`。

| 场景 | 推荐接法 | 需要部署什么 |
| --- | --- | --- |
| **手机上的 ChatGPT / Claude App** | A. 通过本仓库的 MCP 网关 | Cloudflare Worker（本仓库代码） |
| 电脑上的 Claude Code / Cursor / CodeBuddy 等 | B. 直连官方 Hosted MCP（OAuth） | 无 |
| 需要上传本地文件、下载模板等本地能力 | C. 本地 `npx` 运行 | 无（需要 Node.js 18.15+） |

### A. 通过 MCP 网关（手机 AI 用）

手机上的 AI 客户端只支持标准 OAuth 远程连接器，而且不适合在客户端里保存腾讯云密钥。网关用 GitHub 登录做身份验证（只允许你一个账号），在服务端用环境 API Key 换取官方 token，Key 永远不离开 Cloudflare。

部署后在 AI 客户端添加远程 MCP 连接器：

```text
https://<worker 名>.<你的 workers.dev 子域>/mcp
```

部署方式见下文 [第 4 节](#4-部署-mcp-网关)。

### B. 直连官方 Hosted MCP（电脑 IDE 用）

只填 URL，IDE 会打开浏览器走腾讯云登录授权，配置文件里没有密钥：

```json
{
  "mcpServers": {
    "cloudbase": {
      "type": "http",
      "url": "https://tcb-api.cloud.tencent.com/mcp/v1?env_id=<env_id>"
    }
  }
}
```

Claude Code 命令行：

```bash
claude mcp add --transport http cloudbase "https://tcb-api.cloud.tencent.com/mcp/v1?env_id=<env_id>"
```

也可以按官方文档在 `headers` 里放 `X-TencentCloud-SecretId` / `X-TencentCloud-SecretKey` 做静态认证，但这样密钥会落在本地配置文件中，只建议在自动化场景使用。

URL 还支持 `enable_plugins` / `disable_plugins`（逗号分隔，如 `database,functions,hosting,storage,logs`）来限制 AI 能用的工具。

### C. 本地运行

```json
{
  "mcpServers": {
    "cloudbase": {
      "command": "npx",
      "args": ["-y", "@cloudbase/cloudbase-mcp@latest"]
    }
  }
}
```

首次使用会引导登录。本地模式能力最全（包括上传本地文件）。

## 3. CloudBase CLI

```bash
npm i -g @cloudbase/cli            # 命令为 tcb
tcb login                          # 交互式登录；或非交互：
tcb login --cloudbase-api-key "$CLOUDBASE_API_KEY" -e "$ENV_ID"
tcb fn deploy <函数名> --force -e "$ENV_ID"         # 部署云函数（首次自动创建）
tcb fn deploy --all --force -e "$ENV_ID"            # 部署 cloudbaserc.json 中全部云函数
tcb hosting deploy ./dist -e "$ENV_ID"              # 上传静态网站
tcb db / storage / logs / cloudrun ...             # 数据库、存储、日志、云托管
tcb logout
```

### 在 App 仓库里自动部署后端

App 仓库新建 `.github/workflows/cloudbase-deploy.yml`：

```yaml
name: Deploy CloudBase
on:
  push:
    branches: [main]
    paths: ['cloudfunctions/**', 'web/dist/**']
  workflow_dispatch:
permissions:
  contents: read
jobs:
  deploy:
    uses: wenjinliuu/ios-ci-workflows/.github/workflows/cloudbase-deploy.yml@<SHA>
    with:
      env_id: your-env-id
      workdir: .
      functions: getDraws saveTicket      # 或 all；留空则跳过
      functions_dir: cloudfunctions       # 每个函数一个子目录；留空则按 cloudbaserc.json
      hosting_source: ''                  # 例如 web/dist；留空则跳过
    secrets:
      CLOUDBASE_API_KEY: ${{ secrets.CLOUDBASE_API_KEY }}
```

| 输入 | 默认 | 说明 |
| --- | --- | --- |
| `env_id` | 必填 | CloudBase 环境 ID |
| `workdir` | `.` | `cloudbaserc.json` 所在目录 |
| `functions` | `''` | 空格分隔的函数名，或 `all` |
| `functions_dir` | `''` | 函数父目录，传给 `--dir <functions_dir>/<name>` |
| `hosting_source` | `''` | 已构建好的静态文件目录 |
| `hosting_target` | `''` | 静态托管中的目标路径 |
| `cli_version` | `3.8.4` | 固定的 `@cloudbase/cli` 版本 |

Secret：`CLOUDBASE_API_KEY`（环境 API Key）。

## 4. 部署 MCP 网关

先完成一次性准备（详见 [网关 README](../cloudbase-mcp-gateway/README.md#需要准备的东西)）：GitHub OAuth App、KV 命名空间、`COOKIE_ENCRYPTION_KEY`。然后二选一：

### 方式一：本地命令行

```bash
cd cloudbase-mcp-gateway
npm install
# 编辑 wrangler.jsonc 填入 CLOUDBASE_ENV_ID / GITHUB_CLIENT_ID / ALLOWED_GITHUB_LOGIN / KV id
npx wrangler secret put CLOUDBASE_API_KEY
npx wrangler secret put GITHUB_CLIENT_SECRET
npx wrangler secret put COOKIE_ENCRYPTION_KEY
npm run deploy
```

### 方式二：GitHub Actions（适合只有手机时）

在一个**私有**仓库（例如你的部署仓库）新建 `.github/workflows/deploy-gateway.yml`，和 App 仓库一样只放一个很薄的入口，所有 Secret 留在这个私有仓库：

```yaml
name: Deploy CloudBase MCP Gateway
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  deploy:
    uses: wenjinliuu/ios-ci-workflows/.github/workflows/cloudbase-mcp-gateway-deploy.yml@<SHA>
    with:
      ci_revision: <SHA>
      worker_name: cloudbase-mcp-gateway
      cloudbase_env_id: your-env-id
      github_client_id: your-github-oauth-client-id
      allowed_github_login: your-github-login
      kv_namespace_id: your-kv-namespace-id
      public_url: https://cloudbase-mcp-gateway.<你的子域>.workers.dev
    secrets:
      CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
      CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
      CLOUDBASE_API_KEY: ${{ secrets.CLOUDBASE_API_KEY }}
      GITHUB_CLIENT_SECRET: ${{ secrets.GITHUB_CLIENT_SECRET }}
      COOKIE_ENCRYPTION_KEY: ${{ secrets.COOKIE_ENCRYPTION_KEY }}
```

工作流会：按 `ci_revision` 拉取网关代码 → 用输入生成部署配置（拒绝任何 `your-` 占位值）→ 类型检查 → 把提供了的 Secret 写入 Worker（临时文件权限 600，用完删除；某个 Secret 不传则保留 Worker 上现有的值）→ `wrangler deploy` → 若填了 `public_url`，确认 OAuth 元数据可访问且未授权的 `/mcp` 请求返回 401。

`CLOUDFLARE_API_TOKEN`：Cloudflare Dashboard → My Profile → API Tokens → 用 **Edit Cloudflare Workers** 模板创建。`CLOUDFLARE_ACCOUNT_ID` 在 Workers 概览页右侧。

## 5. 凭据总表

| 名称 | 放在哪里 | 用途 |
| --- | --- | --- |
| 环境 API Key | Worker Secret `CLOUDBASE_API_KEY`；App 仓库 Actions Secret `CLOUDBASE_API_KEY` | 网关换 MCP token；CLI 登录 |
| GitHub OAuth Client Secret | Worker Secret `GITHUB_CLIENT_SECRET` | 网关 GitHub 登录 |
| Cookie 签名密钥 | Worker Secret `COOKIE_ENCRYPTION_KEY` | 授权页 Cookie 签名 |
| Cloudflare API Token / Account ID | 部署网关的私有仓库 Actions Secrets | 仅“方式二”部署网关时 |
| 环境 ID、GitHub Client ID、允许的 GitHub 账号、KV id | `wrangler.jsonc` 或部署工作流 `with:` | 非机密配置 |

中央仓库本身不保存上述任何一项。

## 6. 安全提示

- CloudBase MCP 具备写权限（删数据、改云函数、改安全规则），让 AI 执行写操作前先确认。
- 可以用 `disable_plugins` 或单独的只读环境降低风险。
- 网关只允许 `ALLOWED_GITHUB_LOGIN` 一个 GitHub 账号，变量为空时拒绝所有人。
- 发现 Key 泄露：在云开发控制台删除该 API Key，重新创建后更新对应 Secret。
