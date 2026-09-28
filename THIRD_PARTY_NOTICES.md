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
| [XcodeBuildMCP](https://github.com/getsentry/XcodeBuildMCP)（`xcodebuildmcp`） | 2.7.0 | MIT | `build-test.yml`：抓取 Simulator 无障碍 UI 树 |
| [serve-sim](https://github.com/EvanBacon/serve-sim)（`serve-sim`） | 0.1.46 | Apache-2.0 | `live-preview.yml`：Simulator 画面串流、HID 触控、文字输入 |
| [icon-composer-mcp](https://github.com/ethbak/icon-composer-mcp) | 1.1.0 | MIT | `app-icon.yml`：渲染同一图标在 6 种外观模式下的预览图和 1024 市场图 |
| [xcbeautify](https://github.com/cpisciotta/xcbeautify) | 3.2.1 | MIT | `build-test.yml`：整理 xcodebuild 日志（校验 SHA-256） |
| [SwiftLint](https://github.com/realm/SwiftLint) | 0.65.1 | MIT | `build-test.yml` static-checks：App 有 `.swiftlint.yml` 时运行（校验 SHA-256） |
| [SwiftFormat](https://github.com/nicklockwood/SwiftFormat) | 0.63.0 | MIT | `build-test.yml` static-checks：App 有 `.swiftformat` 时以 `--lint` 运行（校验 SHA-256） |
| [cloudflared](https://github.com/cloudflare/cloudflared) | 2026.9.3 | Apache-2.0 | `live-preview.yml`：实时预览的 Quick Tunnel / Named Tunnel |
| [node-http-proxy](https://github.com/http-party/node-http-proxy)（`http-proxy`） | 1.18.1 | MIT | `preview-proxy.cjs`：反向代理画面流与 WebSocket |
| [ws](https://github.com/websockets/ws) | 8.21.0 | MIT | `check-public-preview.cjs`：公网 HID WebSocket 验证 |
| [setup-xcode](https://github.com/maxim-lobanov/setup-xcode) | v1 | MIT | 各工作流：选择 Xcode 版本 |
| [XcodeGen](https://github.com/yonaskolb/XcodeGen) | 2.46.0 | MIT | 各 iOS 工作流：App 使用 `xcodegen` 时生成工程（校验 SHA-256） |
| [PyJWT](https://github.com/jpadilla/pyjwt) | 2.10.1 | MIT | `testflight-release.yml` verify job：`scripts/asc-verify.py` 签发 App Store Connect JWT |
| [@cloudflare/workers-oauth-provider](https://github.com/cloudflare/workers-oauth-provider) | ^0.8.3 | MIT | `cloudbase-mcp-gateway`：OAuth 2.1 服务端（npm 依赖） |
| [Hono](https://github.com/honojs/hono) | ^4.13.8 | MIT | `cloudbase-mcp-gateway`：路由（npm 依赖） |
| [CloudBase CLI](https://www.npmjs.com/package/@cloudbase/cli)（`@cloudbase/cli`） | 3.8.4 | ISC | `cloudbase-deploy.yml`：部署云函数与静态托管 |
| [Wrangler](https://github.com/cloudflare/workers-sdk)（`wrangler`） | ^4.135.0 | MIT OR Apache-2.0 | `cloudbase-mcp-gateway`：类型生成、打包、部署（npm 开发依赖） |
| [Octokit](https://github.com/octokit/octokit.js) | ^5.0.5 | MIT | `cloudbase-mcp-gateway`：读取 GitHub 登录用户（npm 依赖） |

## 3. 设计参考（未复制代码）

| 项目 | 许可 | 参考了什么 |
| --- | --- | --- |
| [native-sim](https://github.com/bidah/native-sim) | MIT（package.json 声明） | 整体思路：GitHub → macOS runner → iOS Simulator → serve-sim → 鉴权网关 → Cloudflare Quick Tunnel → 浏览器。本仓库的 `preview-proxy.cjs`（密码登录 + 接口白名单 + 屏蔽 shell）、`check-public-preview.cjs` 和工作流步骤为针对原生 Swift/Xcode 项目独立实现 |
| [Maestro](https://github.com/mobile-dev-inc/Maestro) | Apache-2.0 | 评估过 Agent 驱动的 UI 自动化；不采用，关键流程由 XCUITest 负责，结果直接进 `.xcresult` |
| [swift-snapshot-testing](https://github.com/pointfreeco/swift-snapshot-testing) | MIT | 快照录制开关对接它的 `SNAPSHOT_TESTING_RECORD` 环境变量和 `__Snapshots__` 目录约定；由 App 自己作为测试依赖引入 |
| [CloudBase AI Toolkit / CloudBase MCP](https://github.com/TencentCloudBase/CloudBase-AI-Toolkit) | MIT | `cloudbase-mcp-gateway` 代理的腾讯云官方 Hosted MCP 服务及其 OAuth 接口；未复制代码 |
