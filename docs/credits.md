# 致谢与第三方许可

本仓库以 [MIT License](../LICENSE) 开源。完整清单与许可文本见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

测试以苹果官方为主（Swift Testing、XCUITest、Test Plan、`performAccessibilityAudit()`），第三方只补苹果没有的部分；周边工具用成熟开源项目，固定版本、运行时下载。

| 项目 | 状态 | 用在哪 | 作用 |
| --- | --- | --- | --- |
| [swift-snapshot-testing](https://github.com/pointfreeco/swift-snapshot-testing) | 采用（App 依赖） | Build & Test | 快照测试，苹果没有官方方案 |
| [swift-dependencies](https://github.com/pointfreeco/swift-dependencies) | 采用（App 依赖） | App 代码 + 测试 | 控制“今天”等依赖，测日期边界 |
| [SwiftLint](https://github.com/realm/SwiftLint) / [SwiftFormat](https://github.com/nicklockwood/SwiftFormat) | 采用 | Build & Test（Linux） | 规范、格式 |
| [xcbeautify](https://github.com/cpisciotta/xcbeautify) | 采用 | Build & Test | 整理日志 |
| [XcodeGen](https://github.com/yonaskolb/XcodeGen) | 采用 | 所有 iOS 工作流 | 用 `project.yml` 生成工程 |
| [XcodeBuildMCP](https://github.com/getsentry/XcodeBuildMCP) | 在用（`xcodebuildmcp@2.7.0`） | Build & Test | 抓 UI 树；升级时包名改为 `mobilebuildmcp` |
| [icon-composer-mcp](https://github.com/ethbak/icon-composer-mcp) | 在用（1.1.0） | App Icon | 渲染 6 种外观预览 |
| [serve-sim](https://github.com/EvanBacon/serve-sim) | 在用（0.1.46） | Live Preview | 模拟器画面和触控 |
| [cloudflared](https://github.com/cloudflare/cloudflared) | 在用（固定版本 + SHA-256） | Live Preview | 公网隧道 |
| [CloudBase MCP / AI Toolkit](https://github.com/TencentCloudBase/CloudBase-AI-Toolkit) | 在用 | 后端 | 官方 MCP，经网关接入 |
| CloudBase Skills | 按需 | App 仓库 | 官方后端技能，AI 用到时安装 |
| [Cloudflare remote-mcp-github-oauth](https://github.com/cloudflare/ai/tree/main/demos/remote-mcp-github-oauth) | 部分代码（MIT） | MCP 网关 | OAuth 辅助文件 |
| [native-sim](https://github.com/bidah/native-sim) | 仅参考 | Live Preview | 借鉴链路设计和保活设置 |
| agent-device | 暂缓 | Live Preview | AI 实时操作模拟器的接口 |
| Sentry | 以后 | App | 上 TestFlight 后接入崩溃与性能监控 |
| AccessibilitySnapshot | 可选 | Build & Test | VoiceOver 快照 |
| SnapshotPreviews | 评估未采用 | — | 用 `#Preview` 自动生成快照 |
| Muter / swift-mutation-testing | 可选体检 | — | 变异测试，衡量测试质量 |
| [Maestro](https://github.com/mobile-dev-inc/Maestro) | 不采用 | — | 由 XCUITest 取代（结果直接进 `.xcresult`，不需要 Java） |
