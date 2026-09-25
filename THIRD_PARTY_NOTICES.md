# Third-Party Notices

本仓库自身代码使用 [MIT License](LICENSE)。下面列出 (1) 本仓库中包含的第三方代码，(2) CI 运行时下载使用、但未包含在本仓库中的第三方工具，(3) 只在设计上参考过、没有复制代码的项目。

## 1. 本仓库包含的第三方代码

### Cloudflare — remote-mcp-github-oauth demo

- 来源：https://github.com/cloudflare/ai/tree/main/demos/remote-mcp-github-oauth
- 许可：MIT License
- 涉及文件：
  - `cloudbase-mcp-gateway/src/workers-oauth-utils.ts`：原样复制
  - `cloudbase-mcp-gateway/src/utils.ts`：有修改（`Props` 类型不再保存 GitHub access token）
  - `cloudbase-mcp-gateway/src/github-handler.ts`：有修改（只允许 `ALLOWED_GITHUB_LOGIN` 登录，不保存 GitHub access token，授权页文案）

```
MIT License

Copyright (c) 2025 Cloudflare, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 2. CI 运行时使用的第三方工具（未包含在本仓库中）

以下工具在 GitHub Actions runner 上按固定版本下载运行，不随本仓库分发，各自遵循其许可证。

| 项目 | 版本 | 许可 | 在本仓库中的用途 |
| --- | --- | --- | --- |
| [XcodeBuildMCP](https://github.com/getsentry/XcodeBuildMCP)（`xcodebuildmcp`） | 2.7.0 | MIT | `agent-preview.yml` 与 `preview-proxy.cjs`：抓取 Simulator 无障碍 UI 树 |
| [serve-sim](https://github.com/EvanBacon/serve-sim)（`serve-sim`） | 0.1.46 | Apache-2.0 | `agent-preview.yml`：Simulator 画面串流、HID 触控、文字输入 |
| [icon-composer-mcp](https://github.com/ethbak/icon-composer-mcp) | 1.1.0 | MIT | `app-icon.yml`：渲染 `.icon` 的 6 种外观和 1024 市场图 |
| [cloudflared](https://github.com/cloudflare/cloudflared) | 2026.9.3 | Apache-2.0 | `agent-preview.yml`：实时预览的 Quick Tunnel / Named Tunnel |
| [node-http-proxy](https://github.com/http-party/node-http-proxy)（`http-proxy`） | 1.18.1 | MIT | `preview-proxy.cjs`：反向代理画面流与 WebSocket |
| [ws](https://github.com/websockets/ws) | 8.21.0 | MIT | `check-public-preview.cjs`：公网 HID WebSocket 验证 |
| [setup-xcode](https://github.com/maxim-lobanov/setup-xcode) | v1 | MIT | 各工作流：选择 Xcode 版本 |
| [XcodeGen](https://github.com/yonaskolb/XcodeGen) | Homebrew 最新 | MIT | 各工作流：App 使用 `xcodegen` 时生成工程 |
| [PyJWT](https://github.com/jpadilla/pyjwt) | pip 最新 | MIT | `testflight-release.yml` verify job：供 App 的注册校验脚本签发 App Store Connect JWT |
| [@cloudflare/workers-oauth-provider](https://github.com/cloudflare/workers-oauth-provider) | ^0.8.3 | MIT | `cloudbase-mcp-gateway`：OAuth 2.1 服务端（npm 依赖） |
| [Hono](https://github.com/honojs/hono) | ^4.13.8 | MIT | `cloudbase-mcp-gateway`：路由（npm 依赖） |
| [Octokit](https://github.com/octokit/octokit.js) | ^5.0.5 | MIT | `cloudbase-mcp-gateway`：读取 GitHub 登录用户（npm 依赖） |

## 3. 设计参考（未复制代码）

| 项目 | 许可 | 参考了什么 |
| --- | --- | --- |
| [native-sim](https://github.com/bidah/native-sim) | MIT（package.json 声明） | 整体思路：GitHub → macOS runner → iOS Simulator → serve-sim → 鉴权网关 → Cloudflare Quick Tunnel → 浏览器。本仓库的 `preview-proxy.cjs`（密码登录 + 接口白名单 + 屏蔽 shell）、`check-public-preview.cjs` 和工作流步骤为针对原生 Swift/Xcode 项目独立实现 |
| [Maestro](https://github.com/mobile-dev-inc/Maestro) | Apache-2.0 | Agent 驱动 UI 自动化（点击/滑动/断言）和 E2E 测试思路。目前未作为依赖使用，UI 检查以 XCTest + XcodeBuildMCP 为主 |
| [Tencent CloudBase Hosted MCP](https://docs.cloudbase.net/) | — | `cloudbase-mcp-gateway` 调用的腾讯云官方 MCP 服务及其 OAuth 接口 |
