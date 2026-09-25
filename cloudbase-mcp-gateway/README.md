# CloudBase MCP Gateway（Cloudflare Worker）

让手机上的 AI 助手（ChatGPT、Claude 等支持远程 MCP 的客户端）**安全地**连接腾讯云开发 CloudBase **官方 Hosted MCP**，从而直接操作 App 后端（数据库、云函数、存储、日志等）。

```text
AI 客户端 ──OAuth──▶ Cloudflare Worker（本网关） ──Bearer token──▶ tcb-api.cloud.tencent.com/mcp/v1 ──▶ CloudBase 环境
            GitHub 登录，只允许一个账号          服务端用 CloudBase API Key 换取官方 MCP token
```

网关本身不运行 CloudBase MCP，只做三件事：

1. **身份验证**：对外是标准 OAuth 2.1 服务器（`@cloudflare/workers-oauth-provider`），用户通过 GitHub 登录，**只允许 `ALLOWED_GITHUB_LOGIN` 指定的账号** 完成授权；未配置时一律拒绝。
2. **换取上游凭据**：在服务端用 `CLOUDBASE_API_KEY` 走腾讯官方 Hosted MCP 的 OAuth（注册 → PKCE 授权 → API Key 校验 → 同意 → 换 token），token 在内存缓存，过期前 60 秒刷新，上游返回 401 时强制刷新一次。
3. **代理 MCP 流量**：`GET/POST/DELETE /mcp` 转发到官方端点；统一 `MCP-Protocol-Version`；去掉客户端的 Cookie、Cloudflare 转发头，以及上游的 `Set-Cookie`、`WWW-Authenticate`、`Location` 等头。CloudBase API Key 永远不会离开 Worker。

## 需要准备的东西

| 项目 | 在哪里创建 | 放在哪里 |
| --- | --- | --- |
| CloudBase 环境 ID | 腾讯云开发控制台 | `wrangler.jsonc` → `vars.CLOUDBASE_ENV_ID` |
| CloudBase API Key | 云开发控制台 → 环境 → API Key 管理 | Worker Secret `CLOUDBASE_API_KEY` |
| GitHub OAuth App | GitHub → Settings → Developer settings → OAuth Apps | Client ID → `vars.GITHUB_CLIENT_ID`；Client Secret → Worker Secret `GITHUB_CLIENT_SECRET` |
| 允许登录的 GitHub 账号 | 你自己的 GitHub 用户名 | `vars.ALLOWED_GITHUB_LOGIN` |
| Cookie 签名密钥 | 本地生成：`openssl rand -hex 32` | Worker Secret `COOKIE_ENCRYPTION_KEY` |
| KV 命名空间 | `npx wrangler kv namespace create OAUTH_KV` | `wrangler.jsonc` → `kv_namespaces[0].id` |

GitHub OAuth App 设置：

- Homepage URL：`https://<worker 名>.<你的子域>.workers.dev`
- Authorization callback URL：`https://<worker 名>.<你的子域>.workers.dev/callback`
- 网关只申请 `read:user` 权限，仅用于确认登录的是谁。

## 部署

需要 Node.js 20+ 和一个 Cloudflare 账号（免费套餐即可）。

```bash
cd cloudbase-mcp-gateway
npm install
npx wrangler login

# 1. 创建 KV，把输出的 id 填进 wrangler.jsonc
npx wrangler kv namespace create OAUTH_KV

# 2. 编辑 wrangler.jsonc：CLOUDBASE_ENV_ID、GITHUB_CLIENT_ID、ALLOWED_GITHUB_LOGIN、KV id

# 3. 写入三个 Secret（交互式输入，不会进入代码或 shell 历史）
npx wrangler secret put CLOUDBASE_API_KEY
npx wrangler secret put GITHUB_CLIENT_SECRET
npx wrangler secret put COOKIE_ENCRYPTION_KEY

# 4. 检查并部署
npm run type-check
npm run deploy
```

部署后的 MCP 地址：

```text
https://<worker 名>.<你的子域>.workers.dev/mcp
```

在 AI 客户端中把它添加为远程 MCP 连接器（例如 ChatGPT 的自定义连接器、Claude 的自定义 Connector），首次使用会跳到 GitHub 登录并授权。

## 端点

| 路径 | 作用 |
| --- | --- |
| `/mcp` | MCP 端点（需要网关签发的 access token） |
| `/authorize` | 授权页（确认 → GitHub 登录） |
| `/callback` | GitHub 回调 |
| `/token` | 换取 / 刷新 token |
| `/register` | MCP 客户端动态注册 |

## 安全边界

- 只有 `ALLOWED_GITHUB_LOGIN` 一个账号能完成授权，并且 `/mcp` 在每次请求时再校验一次；该变量为空时网关拒绝所有人。
- CloudBase API Key、GitHub Client Secret、Cookie 密钥只存在 Cloudflare Worker Secrets 中。
- OAuth state 一次性使用、10 分钟过期、与浏览器会话绑定（`__Host-` Cookie + SHA-256），授权页带 CSRF 保护，禁止被 iframe 嵌入。
- 错误日志会脱敏 token / key。
- CloudBase MCP 拥有写权限（删库、改云函数等），AI 执行写操作前应当让你确认。
- 建议为网关单独创建一个 CloudBase API Key，方便随时吊销。

## 本地开发

```bash
cp .dev.vars.example .dev.vars   # 或手动创建 .dev.vars 写入三个 Secret
npm run dev
```

`.dev.vars` 已在 `.gitignore` 中，不要提交。

## 来源与许可

- `src/index.ts`：Hosted MCP 网关与代理逻辑，本项目原创。
- `src/workers-oauth-utils.ts`（原样复制）、`src/utils.ts` 和 `src/github-handler.ts`（有修改）来自 Cloudflare 的 [remote-mcp-github-oauth](https://github.com/cloudflare/ai/tree/main/demos/remote-mcp-github-oauth) 示例，MIT License，Copyright (c) 2025 Cloudflare, Inc.，详见仓库根目录 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。
