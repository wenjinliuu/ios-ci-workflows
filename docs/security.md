# 安全约定

- 密钥只在 App 仓库的 GitHub Secrets 里，只注入到需要它的步骤；工作流 YAML、日志和提交里不出现明文。中央仓库必须保持 public，也不存任何密钥。
- 使用者的运行跑在他自己的仓库和 runner 分钟数里，Secrets 只在他的运行中使用，我们看不到。
- checkout 一律 `persist-credentials: false`；只有提交快照参考图、提交图标预览的 job 需要保留凭据来推送。
- 默认只需要 `contents: read`。写权限只在三处按需开启：提交快照参考图、提交图标预览（`contents: write`），开验收 Issue（`issues: write`）。TestFlight 复用已有测试结果时只读 `actions` 和 `pull-requests`。这些 job 不声明权限、继承入口文件的令牌，不开对应功能就不用授予。
- App Store Connect `.p8` 以 `600` 权限写入 runner，job 结束前无论成败都会删除；runner 本身用完即销毁。
- Live Preview 的网关只转发模拟器画面和 HID 触控，不转发 serve-sim 带 shell 能力的 `/exec-ws` 和开发者工具；公网地址开放前会自动验证这一点。预览密码 ≥12 位，每个 App 用不同的密码、主机名和 Tunnel token，预览随 job 结束而关闭（最长 20 分钟）。预览构建不要用生产账号或真实用户的敏感数据。
- CloudBase：平时只部署测试环境，打 `v*` 标签才上生产；MCP 网关默认指向测试环境，API Key 只在 Worker 里，AI 客户端拿不到。
- 第三方工具都固定版本；直接下载的二进制都校验 SHA-256。清单见 [versioning.md](versioning.md#外部依赖)。
