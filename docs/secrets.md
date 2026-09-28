# Secrets 与 Variables

全部配置在 **App 仓库**（Settings → Secrets and variables → Actions），中央仓库不存任何密钥。

| 名称 | 类型 | 用于 | 何时需要 | 从哪里来 |
| --- | --- | --- | --- | --- |
| `APPLE_TEAM_ID` | Secret | TestFlight | 发版 | Apple Developer → Membership |
| `APP_STORE_CONNECT_KEY_ID` | Secret | TestFlight | 发版 | App Store Connect API Key |
| `APP_STORE_CONNECT_ISSUER_ID` | Secret | TestFlight | 发版 | App Store Connect API 页面顶部 |
| `APP_STORE_CONNECT_PRIVATE_KEY` | Secret | TestFlight | 发版 | 下载的 `.p8` 文件全文（含首尾两行） |
| `AGENT_PREVIEW_PASSWORD` | Secret | Live Preview | 用 Live Preview | 自己生成，≥12 位，每个 App 不同 |
| `AGENT_PREVIEW_TUNNEL_TOKEN` | Secret | Live Preview | 仅固定域名 | Cloudflare Tunnel token |
| `AGENT_PREVIEW_URL` | **Variable** | Live Preview | 仅固定域名（与上一项成对） | 如 `https://myapp-preview.example.com` |
| `CLOUDBASE_API_KEY` | Secret | CloudBase 部署 | 用 `cloudbase-deploy.yml` | 测试环境的 API Key |
| `CLOUDBASE_PROD_API_KEY` | Secret | CloudBase 部署 | 部署生产环境 | 生产环境的 API Key |

`GITHUB_TOKEN` 由 GitHub 自动提供。`dry_run` 的 TestFlight 运行需要声明的 Secret 名存在，但不会用到签名相关的值。MCP 网关自己的 Secrets 见 [cloudbase.md](cloudbase.md#5-凭据总表)。

## Apple 侧怎么生成

1. **Team ID**：developer.apple.com → Membership details。
2. **App Store Connect API Key**：App Store Connect → 用户和访问 → 集成 → App Store Connect API → 团队密钥 → 生成。
   - 角色建议 **Admin**（或至少 App Manager 并勾选访问“云端管理的分发证书”）：工作流用自动签名 + 云端管理证书，需要能创建和更新描述文件。
   - 记下 **Key ID**、**Issuer ID**，下载 `.p8`（只能下载一次）。
3. **不需要**手动导出 `.p12` 证书或描述文件，导出时由 Xcode 通过 API Key 自动管理签名。
4. 在 Certificates, Identifiers & Profiles 注册 Bundle ID 并勾选需要的能力（iCloud 等）；在 App Store Connect 新建 App。

手动运行 TestFlight 并勾选 `lookup_only`，可以列出团队下全部 Bundle ID 和 App，核对是否注册好。
