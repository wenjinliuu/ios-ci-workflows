# ios-ci-workflows

**一台手机 + AI + GitHub Actions 开发 iOS App 的中央工作流仓库。**

这里放的是所有 iOS App 共用的 GitHub Actions 可复用工作流（`workflow_call`）。每个 App 仓库只需要一个很薄的入口文件、自己的参数和 Secrets，就能在云端 Mac 上完成：图标生成与校验、编译并跑全部测试、输出给人和 AI 读的测试报告（失败原因、快照对比图、无障碍问题）、手机浏览器实时操作模拟器、发版门槛与签名上传 TestFlight、真机验收清单。

![工作流总览](docs/images/workflow-overview.png)

> 完整的分步骤工作流图在本文 [最后](#完整工作流图)。

---

## 目录

- [整体思路](#整体思路)
- [仓库内容](#仓库内容)
- [三个 iOS 可复用工作流](#三个-ios-可复用工作流)
- [接入前准备清单](#接入前准备清单)
- [接入步骤（App 仓库）](#接入步骤app-仓库)
- [Secrets 与 Variables 一览](#secrets-与-variables-一览)
- [Cloudflare 需要部署什么](#cloudflare-需要部署什么)
- [后端（可选）：CloudBase + MCP](#后端可选cloudbase--mcp)
- [日常使用](#日常使用)
- [升级中央工作流](#升级中央工作流)
- [安全约定](#安全约定)
- [常见问题](#常见问题)
- [致谢与开源许可](#致谢与开源许可)
- [完整工作流图](#完整工作流图)

---

## 整体思路

| 角色 | 负责什么 |
| --- | --- |
| 手机 | 唯一的开发设备：给 AI 发指令、看结果、打开实时预览、装 TestFlight |
| AI 编程助手 | GPT / Claude Code / 豆包 / WorkBuddy 等任意能读写 GitHub 仓库的 AI，负责读代码、改代码、补测试、提交，再根据 CI 的测试报告继续修；操作规范见 [`skills/ios-ci-workflows/SKILL.md`](skills/ios-ci-workflows/SKILL.md) |
| App 仓库 | 存 App 代码 + 很薄的工作流入口 + 自己的参数和 Secrets |
| **本仓库**（中央仓库） | 公共 CI 逻辑只写一次，所有 App 按固定 commit 复用 |
| GitHub Actions macOS Runner | 所有必须在 Mac 上做的事：Xcode 编译、Simulator、签名、上传。每次都是全新的云端 Mac，用完即销毁 |
| Cloudflare | 实时预览的公网隧道；（可选）AI 连接后端 MCP 的身份验证层 |
| Apple Developer / App Store Connect | 证书、签名、TestFlight、上架 |

关键约定：

- App 仓库 **按固定 commit SHA** 调用本仓库，中央仓库更新不会悄悄改变任何 App 的行为。
- 运行记录、产物（截图、日志、xcresult、dSYM）都留在 **各自的 App 仓库** 里。
- Secrets 只放在 App 仓库，本仓库不存任何密钥。

## 仓库内容

```
.github/workflows/
  app-icon.yml             # 图标：同步 → 不签名 archive 校验 → 渲染预览图（可选写回仓库）
  agent-preview.yml        # 编译 + 全部测试 + 测试报告 + 截图/UI 树/日志 + 静态检查 + 可选实时预览
  testflight-release.yml   # 发版门槛 → 核对注册 → 不签名 archive → entitlements → 签名上传 → 可选验收 Issue
  cloudbase-deploy.yml     # 可复用：CloudBase CLI 部署云函数 / 静态托管
  cloudbase-mcp-gateway-deploy.yml  # 可复用：部署 CloudBase MCP 网关到 Cloudflare Workers
  cloudbase-mcp-gateway.yml         # 本仓库自检：网关代码类型检查 / lint / 打包
scripts/
  asc-verify.py            # TestFlight 发布前用 App Store Connect API 核对 Bundle ID、App、iCloud 容器
  xcresult-report.py       # 把 Test.xcresult 整理成测试报告（失败原因、快照对比图、无障碍问题）
  preview-proxy.cjs        # 实时预览的密码网关（只转发画面与触控，屏蔽 shell 接口）
  check-public-preview.cjs # 校验公网地址：登录、JPEG 画面帧、HID WebSocket、shell 接口不可访问
skills/ios-ci-workflows/   # 给 AI 的操作手册（SKILL.md）：怎么接入、读报告、写测试、发版
cloudbase-mcp-gateway/     # 可选：让 AI 通过 OAuth 安全连接腾讯云开发官方 Hosted MCP 的 Cloudflare Worker
docs/
  named-preview.md         # 固定域名（Named Tunnel）实时预览的详细配置
  cloudbase.md             # 腾讯云开发：官方 MCP 三种接法、CLI、部署工作流、凭据总表
  images/                  # README 中的流程图
LICENSE                    # MIT
THIRD_PARTY_NOTICES.md     # 第三方代码、运行时工具与参考项目
```

## 三个 iOS 可复用工作流

> CloudBase 相关的两个可复用工作流见 [后端（可选）：CloudBase + MCP](#后端可选cloudbase--mcp)。

### 1. `app-icon.yml` — App 图标

Liquid Glass 图标包含图层和材质，所以 App 仓库保留 SVG 图层素材，由 CI 生成 `.icon` 图标包并验证。

两个并行 job（`macos-26`，Xcode 26.6）：

1. **native-validation**：运行 `sync_command` 同步图标 → `generate_command` 生成工程 → 不签名 `xcodebuild archive`，确认 `Assets.car` 和 `AppIcon*.png` 真正编进了 App，构建日志中出现图标冲突/报错即失败。
2. **preview**（失败不阻塞）：用 `icon-composer-mcp` 渲染**同一个图标**在 6 种外观模式下的预览图（Default / Dark / TintedLight / TintedDark / ClearLight / ClearDark，对应 iOS 26 主屏幕的图标显示模式），外加 1 张 1024 市场图，共 7 个 PNG，上传为产物 `app-icon-<sha>`。这些只是预览，真正编进 App 的是 `.icon` 图标包，由系统在运行时渲染。
3. **publish-previews**（可选，`commit_previews: true`）：只在推送到分支时，把 7 张图写进 App 仓库的 `previews_dir`，并生成一个图片表格 `README.md`，在 GitHub 上打开目录就能直接看；由机器人提交。用任务自带的令牌推送不会再触发工作流，所以不会循环；入口文件的 `paths` 仍建议排除这个目录。需要入口文件授予 `contents: write`，不开这个功能就不用授予。

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `workdir` | ✅ | App 工程所在目录（仓库根目录填 `.`） |
| `project` | ✅ | `.xcodeproj` 路径（相对 `workdir`） |
| `scheme` | ✅ | 主 App scheme |
| `icon_path` | ✅ | `.icon` 图标包路径，里面必须有 `icon.json` |
| `sync_command` | ✅ | 把 SVG 图层同步到 `.icon` 的命令；不需要可填 `true` |
| `generate_command` | ✅ | 生成工程的命令，如 `xcodegen generate`；含 `xcodegen` 时会自动 `brew install xcodegen`；已提交 `.xcodeproj` 可填 `true` |
| `commit_previews` | | 默认 `false`；`true` 时把预览图写回仓库 |
| `previews_dir` | | 默认 `DesignAssets/AppIcon/previews`，相对仓库根目录 |

### 2. `agent-preview.yml` — Build · Test · Agent Preview

CI 是测试的唯一入口：每次推送和 PR 都把 App 的全部测试从头跑一遍，输出一份人和 AI 都能直接读的测试报告。测试以苹果官方工具为主，第三方只补苹果没有的部分；AI 看截图做“UI 自检”不可靠，只作补充。

**测试分层**（测试本身写在 App 仓库，中央仓库负责跑和汇报）：

| 层 | 工具 | 负责抓什么 |
| --- | --- | --- |
| 逻辑测试（最多） | Swift Testing / XCTest | 业务规则、日期边界、数据存取；参数化测试一次喂几十组数据 |
| 时间控制 | [swift-dependencies](https://github.com/pointfreeco/swift-dependencies) | 把“今天”固定成春节、闰月、跨年等边界日期 |
| 快照测试（视觉回归主力） | [swift-snapshot-testing](https://github.com/pointfreeco/swift-snapshot-testing) | 文字截断、元素重叠、布局错位；逐像素对比参考图 |
| 关键流程（只写 3～5 条） | XCUITest | 核心用户路径 |
| 无障碍审计 | `performAccessibilityAudit()`（在 XCUITest 里调用） | 文字截断、对比度不足、点击区域太小、缺标签 |
| 多环境组合 | Test Plan（`.xctestplan`） | 浅色/深色、中/英文、大字号，同一套测试跑多种配置 |
| 静态检查 | SwiftLint、SwiftFormat（Linux runner） | 代码规范、格式 |

App 仓库的推荐布局：

```
MyAppTests/          逻辑测试
MyAppSnapshotTests/  快照测试 + __Snapshots__ 参考图
MyAppUITests/        关键流程 + 无障碍审计（测试名带 Accessibility）
MyApp.xctestplan     测试计划（可选）
```

**simulator job**（每次都跑，`macos-26`）：

1. 同步图标、生成工程（缓存 Swift Packages）
2. 选择并启动 Simulator（默认 iPhone 17 Pro / iOS 26）。机型不存在时在同一 runtime 内回退并给出警告；快照依赖固定机型，看到这个警告先确认参考图是否还适用
3. `xcodebuild test`（不签名）跑 scheme，或 `test_plan` 指定的测试计划；日志经 xcbeautify 整理，原始日志另存 `xcodebuild.log`。**测试失败不会中断后面的步骤**
4. 安装并启动 App，校验 Bundle ID，截图 `launch.png`，导出 App 日志；用 XcodeBuildMCP 抓取无障碍 UI 树 `ui-tree.json`（最多重试 3 次）
5. **测试报告**：`scripts/xcresult-report.py` 读 `Test.xcresult`，列出失败的测试及原因、快照不一致（附 reference / failure / difference 图）、无障碍问题、新录制的快照参考图，写进 job summary 和 `report/report.md`、`report/report.json`
6. **可选实时预览**（仅手动触发且 `live_preview=true`，编译成功即可，测试失败也能开）：
   `serve-sim`（画面流 + 触控）→ `preview-proxy.cjs`（密码网关）→ `cloudflared`（公网地址）→ 手机浏览器。
   预览地址会以 notice 显示在正在运行的 job 日志里，也会写入 job summary。最长 20 分钟
7. 上传产物，然后按下面的规则判定通过/失败

**static-checks job**（`ubuntu-latest`，不耗 macOS 分钟）：App 仓库根目录或 `workdir` 里有 `.swiftlint.yml` 就跑 SwiftLint，有 `.swiftformat` 就跑 `swiftformat --lint`；问题直接标在 PR 的代码行上。都没有就跳过。

**通过/失败规则**：

| 情况 | 结果 |
| --- | --- |
| 编译失败 | 失败，报告列出 `error:` 行 |
| 逻辑测试、关键流程失败 | 失败 |
| 快照不一致 | 失败；`record_snapshots=true` 时不算，改为重新录制 |
| 无障碍审计失败（测试名匹配 `accessibility_test_pattern`） | 默认只警告；问题清干净后把 `accessibility_audit` 改成 `fail` |
| `xcodebuild` 非零退出但报告里没有失败（测试进程崩溃等） | 失败 |

**快照录制**：界面有意改动时，手动运行并勾选 `record_snapshots`。CI 以 `SNAPSHOT_TESTING_RECORD=failed` 运行测试，只重录不一致的快照；新录制的参考图（包括第一次运行时新增的）打包为产物 `recorded-snapshots-<run>`。打开 `commit_recorded_snapshots` 后，CI 会把它们直接提交回这次运行的分支，AI 不需要下载产物（很多 AI 环境的网络下载不了 GitHub 产物）；没打开就要下载产物、按原路径解压提交。用任务令牌推送的提交不会触发新的运行，提交后再手动跑一次 Build & Test 确认。快照对系统版本很敏感，参考图只在 CI 上生成。

**产物**（保留 7 天，录制的快照 14 天）：

| 产物 | 内容 |
| --- | --- |
| `agent-preview-<run>` | `report/`（报告 + 失败附件）、`launch.png`、`ui-tree.json`、`app.log`、`xcodebuild.log` |
| `agent-preview-xcresult-<run>` | `Test.xcresult`，可用 Xcode 打开 |
| `recorded-snapshots-<run>` | 新录制的快照参考图（有才上传） |

| 输入 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `workdir` / `project` / `scheme` | ✅ | | 同上 |
| `bundle_id` | ✅ | | 用于校验构建产物和启动 App |
| `sync_command` / `generate_command` | ✅ | | 同上 |
| `ci_revision` | ✅ | | **必须和 `uses:` 里的 SHA 一致**，按这个 commit 拉取 `scripts/` |
| `ci_repository` | | `wenjinliuu/ios-ci-workflows` | 拉取 `scripts/` 的仓库；fork 后改成自己的 |
| `test_plan` | | `''` | 测试计划名；空则跑 scheme 默认的测试 |
| `record_snapshots` | | `false` | 重新录制不一致的快照 |
| `commit_recorded_snapshots` | | `false` | 录制模式下把新参考图提交回运行的分支（仅 `workflow_dispatch`），需要入口文件授予 `contents: write` |
| `accessibility_audit` | | `warn` | `warn` 只警告，`fail` 让无障碍问题阻断 CI |
| `accessibility_test_pattern` | | `(?i)accessibility` | 匹配测试名（如 `MyAppUITests/AccessibilityTests/testAudit()`）的正则，命中的失败算无障碍问题 |
| `simulator_name` | | `iPhone 17 Pro` | Simulator 机型 |
| `ios_runtime` | | `26` | iOS runtime 版本（包含匹配） |
| `live_preview` | | `false` | 是否开启实时预览（只在 `workflow_dispatch` 下生效） |
| `preview_minutes` | | `12` | 预览时长，1–20 分钟 |
| `public_preview_url` | | `''` | 固定域名预览地址，一般传 `${{ vars.AGENT_PREVIEW_URL }}` |

| Secret | 必填 | 说明 |
| --- | --- | --- |
| `AGENT_PREVIEW_PASSWORD` | 开启实时预览时必填 | 预览登录密码，至少 12 位 |
| `AGENT_PREVIEW_TUNNEL_TOKEN` | 仅固定域名预览 | Cloudflare Named Tunnel 的 token |

### 3. `testflight-release.yml` — TestFlight Release

建议只在 **手动触发** 或推送 **`v*` 标签** 时调用。

1. **gate**（可选，Ubuntu）：设置了 `build_workflow` 时，要求这个提交的 Build & Test 是绿的，不绿不发；还在跑就等，最多 `build_wait_minutes` 分钟。`dry_run` / `lookup_only` 时跳过。需要入口文件授予 `actions: read`
1. **verify**（Ubuntu，省 macOS 时长）：不是 dry run 时，用本仓库的 `scripts/asc-verify.py` 通过 App Store Connect API 核对 Bundle ID 已注册、App 已创建；Bundle ID 或 App 缺失都在打包前失败，而不是等到签名。设置了 `icloud_container` 时还会读出 App ID 实际勾选的 iCloud 容器，供 `icloud-verified` 模式决定是否嵌入 iCloud 权限
2. **release**（macOS）：
   - 同步图标、生成工程（注入 `DEVELOPMENT_TEAM`）
   - 生成版本号：build number 默认用 `GITHUB_RUN_NUMBER`；可指定 `marketing_version`
   - 不签名 archive → 校验图标、Bundle ID、显示名
   - 按 `entitlement_mode` 把 entitlements 嵌入 archive
   - `xcodebuild -exportArchive` + App Store Connect API Key **自动签名**（云端管理证书，`-allowProvisioningUpdates`）并直接上传 TestFlight
   - 上传 dSYM；可选导出并检查 iCloud entitlement 报告
   - 无论成功与否都会删除 runner 上的 API Key
3. **acceptance**（可选，`acceptance_issue: true`）：上传成功后在 App 仓库开一个“<App> <版本> (<build>) 发版验收”Issue，内容是带勾选框的真机清单：固定项来自 `acceptance_checklist`，本次项来自 `acceptance_extra`（AI 按这次改动写）。测试员在手机 GitHub App 里打勾、评论、配截图，AI 下次读这个 Issue 修问题。需要入口文件授予 `issues: write`

可选任务（gate、acceptance）不在工作流里声明权限，而是继承入口文件给的令牌权限：不开这些功能的 App 不用多授予任何权限；开了但权限不够时会报出缺哪一项。

`dry_run=true` 时只打包不上传，不需要任何签名步骤，适合先验证工程能正常 archive。

| 输入 | 默认 | 说明 |
| --- | --- | --- |
| `workdir` / `project` / `scheme` / `bundle_id` / `sync_command` / `generate_command` | | 必填，同上 |
| `entitlements_path` | `''` | entitlements 文件路径 |
| `entitlement_mode` | `none` | `none` 不嵌入；`best-effort` 失败不阻塞；`icloud-verified` 只有 verify 确认 iCloud 可用时才嵌入；其他任意值 = 严格嵌入 |
| `icloud_container` | `''` | 如 `iCloud.com.example.app`，会校验 entitlements 中存在 |
| `lookup_only` | `false` | 只列出团队下全部 Bundle ID 与 App（名称、SKU、能力、iCloud 容器），不打包 |
| `dry_run` | `false` | 只 archive 不签名不上传 |
| `build_number` | `''` | 自定义 build number（纯数字） |
| `marketing_version` | `''` | 版本号，如 `1.2` / `1.2.3` |
| `display_name` | `''` | 期望的 `CFBundleDisplayName`，不一致即失败 |
| `expected_team_id` | `''` | 防止用错 Team 的保护校验 |
| `inspect_icloud` | `false` | 额外导出一份本地包并输出 entitlement 报告 |
| `artifact_prefix` | `''` | dSYM 产物名前缀 |
| `ci_revision` | 必填 | **必须和 `uses:` 里的 SHA 一致**，verify 按这个 commit 拉取 `scripts/asc-verify.py` |
| `ci_repository` | `wenjinliuu/ios-ci-workflows` | 拉取 `scripts/` 的仓库；fork 后改成自己的 |
| `build_workflow` | `''` | 发版门槛要检查的工作流文件名，如 `ios-build.yml`；空则不检查 |
| `build_wait_minutes` | `30` | Build & Test 还在跑时最多等多久 |
| `acceptance_issue` | `false` | 上传成功后开发版验收 Issue |
| `acceptance_checklist` | `.github/release-checklist.md` | 固定项清单（Markdown 勾选列表） |
| `acceptance_extra` | `.github/release-checklist-current.md` | 本次项清单，没有这个文件就写“本次没有额外项” |

| Secret（全部必填） | 说明 |
| --- | --- |
| `APPLE_TEAM_ID` | 10 位 Team ID |
| `APP_STORE_CONNECT_KEY_ID` | API Key 的 Key ID |
| `APP_STORE_CONNECT_ISSUER_ID` | API Key 的 Issuer ID |
| `APP_STORE_CONNECT_PRIVATE_KEY` | `.p8` 文件的 **完整文本内容**（含 `-----BEGIN PRIVATE KEY-----` 首尾行） |

用了 iCloud 的 App 统一使用 `entitlement_mode: icloud-verified` 并填写 `icloud_container`（缺少容器会直接报错）。只有 Bundle ID 开启了 iCloud 能力、App ID 上确实勾选了该容器时，才把 iCloud 权限嵌入包内；否则（包括首次发布还没有描述文件可查）跳过 iCloud 权限并给出警告，照常上传，App 应把数据退回存到本机。

---

## 接入前准备清单

### 账号

- [ ] **GitHub 账号**，App 仓库开启 Actions。macOS runner 消耗较多额度，私有仓库请留意 Actions 分钟数
- [ ] **Apple Developer Program**（付费会员，真机测试和上架必需）
- [ ] **App Store Connect** 中已创建该 App（Bundle ID 已注册）——上传 TestFlight 前必须完成
- [ ] （可选）**Cloudflare 账号**（免费即可）——只有固定域名预览或 CloudBase MCP 网关才需要；默认的实时预览（Quick Tunnel）**不需要任何 Cloudflare 账号或配置**
- [ ] （可选）**腾讯云 CloudBase** 环境——App 需要后端时

### App 仓库需要具备

- [ ] 一个可在 `workdir` 下构建的 Xcode 工程：已提交 `.xcodeproj`，或用 XcodeGen 的 `project.yml` 生成
- [ ] 主 App scheme 里包含测试 target（`xcodebuild test` 要能跑）；测试布局见上面的“测试分层”
- [ ] 不签名也能编译（CI 用 `CODE_SIGNING_ALLOWED=NO` 构建）
- [ ] Liquid Glass 图标包 `*.icon`（含 `icon.json`），以及把 SVG 图层同步进去的脚本（没有可以用 `true` 代替 `sync_command`）
- [ ] 工程 Release 配置能 archive（`generic/platform=iOS`）
- [ ] （可选）entitlements 文件（iCloud 等能力）

### Apple 侧需要生成的东西

1. **Team ID**：developer.apple.com → Membership details。
2. **App Store Connect API Key**：App Store Connect → 用户和访问 → 集成 → App Store Connect API → 团队密钥 → 生成。
   - 角色建议 **Admin**（或至少 App Manager 并勾选访问“云端管理的分发证书”），因为工作流使用自动签名 + 云端管理证书，需要能创建/更新描述文件。
   - 记录 **Key ID**、**Issuer ID**，下载 `.p8`（只能下载一次）。
3. **不需要** 手动导出 `.p12` 证书或 Provisioning Profile：导出时由 Xcode 通过 API Key 自动管理签名。
4. 在 Certificates, Identifiers & Profiles 中注册 Bundle ID，并勾选 App 需要的能力（iCloud 等）；在 App Store Connect 中新建 App。

---

## 接入步骤（App 仓库）

### 第 1 步：确定要固定的 commit

找到本仓库 `main` 上想使用的 commit SHA（40 位），下面示例中记为 `<SHA>`。所有 `uses:` 以及 `ci_revision` 都填这个值。

### 第 2 步：配置 Secrets 和 Variables

App 仓库 → Settings → Secrets and variables → Actions，按 [Secrets 与 Variables 一览](#secrets-与-variables-一览) 添加。

### 第 3 步：添加入口工作流

下面三个文件放在 App 仓库的 `.github/workflows/`，所有 App 使用同一套写法，只替换 `MyApp`、路径、Bundle ID 等自己的参数。三个文件里的 `<SHA>` 必须一致。

**`.github/workflows/icon-preview.yml`**

```yaml
name: App Icon Preview

on:
  push:
    branches: [main]
    paths:
      - "DesignAssets/AppIcon/**"
      - "!DesignAssets/AppIcon/previews/**"
      - "MyApp/Resources/AppIcon.icon/**"
      - "project.yml"
      - "Scripts/sync-app-icon.sh"
      - ".github/workflows/icon-preview.yml"
  workflow_dispatch:

permissions:
  contents: read   # 打开 commit_previews 时改成 write

concurrency:
  group: app-icon-${{ github.ref }}
  cancel-in-progress: true

jobs:
  icon:
    uses: wenjinliuu/ios-ci-workflows/.github/workflows/app-icon.yml@<SHA>
    with:
      workdir: .
      project: MyApp.xcodeproj
      scheme: MyApp
      icon_path: MyApp/Resources/AppIcon.icon
      sync_command: bash Scripts/sync-app-icon.sh
      generate_command: xcodegen generate
      # commit_previews: true   # 把预览图写回 DesignAssets/AppIcon/previews/
```

**`.github/workflows/ios-build.yml`**

```yaml
name: Build & Test / Agent Preview

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
    inputs:
      simulator_name:
        description: "iPhone simulator model"
        type: string
        default: iPhone 17 Pro
      ios_runtime:
        description: "Installed iOS runtime (for example 26)"
        type: string
        default: '26'
      live_preview:
        description: "Open authenticated browser preview (requires AGENT_PREVIEW_PASSWORD secret)"
        type: boolean
        default: false
      preview_minutes:
        description: "Live preview lifetime, 1-20 minutes"
        type: number
        default: 12
      record_snapshots:
        description: "Re-record changed snapshot references and upload them"
        type: boolean
        default: false

permissions:
  contents: write   # 只有录制快照后提交参考图的任务会写，其余任务固定只读

concurrency:
  group: agent-preview-${{ github.ref }}
  cancel-in-progress: true

jobs:
  preview:
    uses: wenjinliuu/ios-ci-workflows/.github/workflows/agent-preview.yml@<SHA>
    with:
      workdir: .
      project: MyApp.xcodeproj
      scheme: MyApp
      bundle_id: com.example.myapp
      sync_command: bash Scripts/sync-app-icon.sh
      generate_command: xcodegen generate
      simulator_name: ${{ inputs.simulator_name || 'iPhone 17 Pro' }}
      ios_runtime: ${{ inputs.ios_runtime || '26' }}
      live_preview: ${{ inputs.live_preview || false }}
      preview_minutes: ${{ fromJSON(format('{0}', inputs.preview_minutes || '12')) }}
      public_preview_url: ${{ vars.AGENT_PREVIEW_URL || '' }}
      record_snapshots: ${{ inputs.record_snapshots || false }}
      commit_recorded_snapshots: true
      ci_revision: <SHA>
      # test_plan: MyApp        # 有 .xctestplan 时填它的名字
    secrets:
      AGENT_PREVIEW_PASSWORD: ${{ secrets.AGENT_PREVIEW_PASSWORD }}
      AGENT_PREVIEW_TUNNEL_TOKEN: ${{ secrets.AGENT_PREVIEW_TUNNEL_TOKEN }}
```

**`.github/workflows/testflight.yml`**

```yaml
name: TestFlight

on:
  workflow_dispatch:
    inputs:
      build_number:
        description: "Build number (blank: GitHub run number)"
        type: string
        required: false
      marketing_version:
        description: "Marketing version override (blank: project default)"
        type: string
        required: false
      lookup_only:
        description: "Only verify Apple registration; do not archive or upload"
        type: boolean
        default: false
      dry_run:
        description: "Unsigned archive only; never upload"
        type: boolean
        default: false
  push:
    tags: ["v*"]

permissions:
  contents: read
  actions: read    # 发版门槛读 Build & Test 的结果
  issues: write    # 开发版验收 Issue

concurrency:
  group: myapp-testflight
  cancel-in-progress: false

jobs:
  release:
    uses: wenjinliuu/ios-ci-workflows/.github/workflows/testflight-release.yml@<SHA>
    with:
      workdir: .
      project: MyApp.xcodeproj
      scheme: MyApp
      bundle_id: com.example.myapp
      sync_command: bash Scripts/sync-app-icon.sh
      generate_command: xcodegen generate
      build_number: ${{ inputs.build_number || '' }}
      marketing_version: ${{ inputs.marketing_version || '' }}
      lookup_only: ${{ inputs.lookup_only || false }}
      dry_run: ${{ inputs.dry_run || false }}
      artifact_prefix: myapp-
      build_workflow: ios-build.yml
      acceptance_issue: true
      ci_revision: <SHA>
      # 以下按 App 需要选填：
      # display_name: MyApp
      # expected_team_id: ABCDE12345
      # entitlements_path: MyApp/Resources/MyApp.entitlements
      # entitlement_mode: icloud-verified
      # icloud_container: iCloud.com.example.myapp
    secrets:
      APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
      APP_STORE_CONNECT_KEY_ID: ${{ secrets.APP_STORE_CONNECT_KEY_ID }}
      APP_STORE_CONNECT_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_ISSUER_ID }}
      APP_STORE_CONNECT_PRIVATE_KEY: ${{ secrets.APP_STORE_CONNECT_PRIVATE_KEY }}
```

### 第 4 步：逐步验证

1. 推送一次代码 → **Build & Test** 的 job summary 里应有“测试报告”，产物里有报告、截图、UI 树、日志。
2. 手动运行 **Build & Test**，勾选 `live_preview` → 在运行中的 job 日志里找到预览地址，用手机打开、输入密码。
3. 手动运行 **TestFlight**，先勾选 `lookup_only` → 确认 Bundle ID 和 App 都已注册；再勾选 `dry_run` → 确认 archive 成功。
4. 再不勾 `dry_run` 运行一次 → 在 App Store Connect / TestFlight 看到新 build。
5. 以后发版只需推送 `v1.2.3` 这样的标签。

---

## Secrets 与 Variables 一览

全部配置在 **App 仓库**（Settings → Secrets and variables → Actions），本仓库不需要任何 Secret。

| 名称 | 类型 | 用于 | 何时需要 | 从哪里来 |
| --- | --- | --- | --- | --- |
| `APPLE_TEAM_ID` | Secret | TestFlight | 上传 TestFlight | Apple Developer → Membership |
| `APP_STORE_CONNECT_KEY_ID` | Secret | TestFlight | 上传 TestFlight | App Store Connect API Key |
| `APP_STORE_CONNECT_ISSUER_ID` | Secret | TestFlight | 上传 TestFlight | App Store Connect API 页面顶部 |
| `APP_STORE_CONNECT_PRIVATE_KEY` | Secret | TestFlight | 上传 TestFlight | 下载的 `.p8` 文件全文 |
| `AGENT_PREVIEW_PASSWORD` | Secret | 实时预览 | 开启 `live_preview` | 自己生成，≥12 位，每个 App 不同 |
| `AGENT_PREVIEW_TUNNEL_TOKEN` | Secret | 实时预览 | 仅固定域名预览 | Cloudflare Tunnel token |
| `AGENT_PREVIEW_URL` | **Variable** | 实时预览 | 仅固定域名预览（与上一项成对） | 如 `https://myapp-preview.example.com` |
| `CLOUDBASE_API_KEY` | Secret | CloudBase 部署 | 仅当 App 调用 `cloudbase-deploy.yml` | 云开发控制台 → 环境 → API Key 管理 |

> `dry_run=true` 的 TestFlight 运行需要声明的 Secret 名存在，但不会使用它们。
> `GITHUB_TOKEN` 由 GitHub 自动提供，无需配置。

---

## Cloudflare 需要部署什么

**结论：默认什么都不用部署。** 实时预览默认使用 Cloudflare 的 Quick Tunnel，它是匿名的，不需要账号、域名或 token，这也是三个 App 至今从没配置过 Cloudflare 却能在手机上看到模拟器的原因。只有下面 B、C 两种可选能力才需要 Cloudflare 账号。

| 能力 | 需要 Cloudflare 账号？ | 要部署什么 |
| --- | --- | --- |
| A. 实时预览（默认） | 否 | 无 |
| B. 实时预览固定域名 | 是，且需要托管在 Cloudflare 的域名 | 每个 App 一条 Tunnel + 主机名 |
| C. AI 连接 CloudBase 后端 | 是（免费即可） | 1 个 Worker + 1 个 KV + 3 个 Worker Secrets |

### A. 实时预览：默认 Quick Tunnel（零配置）

链路：`serve-sim`（仅监听 `127.0.0.1:3200`）→ `preview-proxy.cjs` 密码网关（`127.0.0.1:3210`）→ `cloudflared` Quick Tunnel → 手机浏览器。

工作流在 runner 上下载固定版本的 `cloudflared`（校验 SHA-256），创建临时 `*.trycloudflare.com` 地址。开放给你之前会通过这个公网地址自动验证：密码登录、JPEG 画面帧、HID WebSocket，以及 shell 接口 `/exec-ws` 返回 404。DNS 迟迟不能解析时会重新申请地址，最多 4 次。地址只在 job 运行期间有效，每次都不同。

### B. 实时预览：固定域名 Named Tunnel（可选）

只有当 Quick Tunnel 在你的网络下经常无法解析，或者想要固定地址时才需要。需要一个托管在 Cloudflare 的域名。**每个 App 一条独立的 Tunnel 和主机名**，避免同时预览时串到别的模拟器。

1. Cloudflare Dashboard → **Networking → Tunnels** → 创建远程管理（remotely managed）的 Tunnel。
2. 添加 **Published application** 路由，例如 `myapp-preview.example.com` → Service `http://127.0.0.1:3210`，**不要**加路径限制（登录、MJPEG、WebSocket 都要能到达网关）。
3. 在 App 仓库添加 Variable `AGENT_PREVIEW_URL`（`https://myapp-preview.example.com`）和 Secret `AGENT_PREVIEW_TUNNEL_TOKEN`（该 Tunnel 的 token）。
4. （可选）在该主机名上再套一层 Cloudflare Access。

两项必须同时设置，否则工作流直接报错；都不设置时自动使用 Quick Tunnel。详见 [docs/named-preview.md](docs/named-preview.md)。

### C. AI 连接后端：CloudBase MCP 网关（可选）

代码在 [`cloudbase-mcp-gateway/`](cloudbase-mcp-gateway/)，可以本地 `wrangler deploy`，也可以用可复用工作流 `cloudbase-mcp-gateway-deploy.yml` 从手机触发部署。完整步骤见 [docs/cloudbase.md](docs/cloudbase.md)。

```text
AI 客户端 ──OAuth（GitHub 登录，仅允许一个账号）──▶ Cloudflare Worker ──▶ 腾讯云开发官方 Hosted MCP ──▶ CloudBase 环境
```

| Cloudflare 资源 | 名称 | 作用 |
| --- | --- | --- |
| Worker | 默认 `cloudbase-mcp-gateway` | OAuth 2.1 服务端 + MCP 代理，对外地址 `https://<worker>.<子域>.workers.dev/mcp` |
| KV 命名空间 | 绑定名 `OAUTH_KV` | OAuth 客户端注册、授权码、token、一次性 state |
| Worker 变量 | `CLOUDBASE_ENV_ID`、`GITHUB_CLIENT_ID`、`ALLOWED_GITHUB_LOGIN` | 环境 ID、GitHub OAuth App ID、唯一允许登录的 GitHub 账号 |
| Worker Secrets | `CLOUDBASE_API_KEY`、`GITHUB_CLIENT_SECRET`、`COOKIE_ENCRYPTION_KEY` | 用 `wrangler secret put` 写入，不进代码 |

CloudBase API Key 只保存在 Worker 里，由网关在服务端换取官方 MCP token，AI 客户端永远拿不到它。

---

## 后端（可选）：CloudBase + MCP

App 需要后端时使用腾讯云开发 CloudBase（数据库、云函数、云存储、静态托管、日志、身份认证）。本仓库包含全部接入所需内容，**完整说明见 [docs/cloudbase.md](docs/cloudbase.md)**：

| 需求 | 用什么 |
| --- | --- |
| 手机上的 AI 直接查数据、改集合、部署函数、看日志 | 官方 Hosted MCP + 本仓库 [MCP 网关](#c-ai-连接后端cloudbase-mcp-网关可选) |
| 电脑 IDE（Claude Code / Cursor）里的 AI 操作后端 | 直连官方 Hosted MCP（OAuth，无需部署） |
| 推送代码后自动部署云函数 / 静态网站 | 可复用工作流 `cloudbase-deploy.yml`（CloudBase CLI `tcb`） |

一个 **环境 API Key**（云开发控制台 → API Key 管理）就能同时用于 MCP 网关和 CLI 登录（`tcb login --cloudbase-api-key <key> -e <envId>`）。App 仓库调用示例：

```yaml
jobs:
  deploy:
    uses: wenjinliuu/ios-ci-workflows/.github/workflows/cloudbase-deploy.yml@<SHA>
    with:
      env_id: your-env-id
      functions: all            # 或空格分隔的函数名
      hosting_source: web/dist  # 可选
    secrets:
      CLOUDBASE_API_KEY: ${{ secrets.CLOUDBASE_API_KEY }}
```

目前三个 App 都还没有接入 CLI 部署工作流。

---

## 日常使用

| 我想… | 怎么做 |
| --- | --- |
| 改代码并看结果 | 让 AI 修改并补测试后推送；等 **Build & Test** 完成，AI 读 job summary 或产物里的测试报告继续修 |
| 有意改了界面 | 在工作分支上手动运行 **Build & Test**，勾选 `record_snapshots`；CI 把新参考图提交回这个分支，再跑一次 Build & Test 确认变绿 |
| 在手机上实际点一点 | 手动运行 **Build & Test**，勾选 `live_preview`；在运行中的 job 日志 notice 或 summary 里打开地址，输入密码。可点击、滑动、输入文字、查看 UI Tree 和日志 |
| 换机型 / iOS 版本 | 手动运行时修改 `simulator_name`、`ios_runtime` |
| 看图标效果 | 修改图标素材后，看 **App Icon** 产物里的预览图；开了 `commit_previews` 就直接打开仓库里的预览目录 |
| 发内测 | 推 `v*` 标签，或手动运行 **TestFlight**；上传后在验收 Issue 里逐项打勾 |
| 只验证能不能打包 | 手动运行 **TestFlight**，勾选 `dry_run` |
| 核对 Apple 侧注册情况 | 手动运行 **TestFlight**，勾选 `lookup_only` |

## 升级中央工作流

1. 在本仓库修改并合并到 `main`。
2. 在每个 App 仓库把三个入口文件里的 `uses: ...@<旧SHA>` 和 `ci_revision: <旧SHA>` **一起** 改成同一个新 SHA。
3. 先手动跑一次 Build & Test 和 TestFlight `dry_run` 确认无误。

修改签名、描述文件或上传相关步骤前，先仔细检查现有 TestFlight 运行的输出。

## 安全约定

- 所有密钥只存放在 App 仓库的 GitHub Secrets 中，只注入到需要它的步骤；工作流 YAML 和日志中不得出现明文 token。
- App Store Connect `.p8` 以 `600` 权限写入 runner，job 结束前无论成败都会删除；runner 本身用完即销毁。
- checkout 一律 `persist-credentials: false`（只有写回图标预览图的任务需要保留凭据来推送）。
- 必需的任务固定 `contents: read`；可选任务（快照参考图提交、图标预览写回、发版门槛、验收 Issue）不声明权限、继承入口文件给的令牌，入口文件只授予自己用到的那几项。
- 实时预览网关只转发模拟器画面和 HID 触控，**不会**转发 serve-sim 带 shell 能力的 `/exec-ws` 和开发者工具；公网地址开放前会自动验证这一点。
- 预览密码 ≥12 位，每个 App 使用不同的密码、主机名和 Tunnel token。预览随 job 结束而关闭（最长 20 分钟）。
- 预览构建不要使用生产账号或真实用户敏感数据。
- 第三方工具都固定版本：`xcodebuildmcp@2.7.0`、`serve-sim@0.1.46`、`icon-composer-mcp@1.1.0`；直接下载的二进制都校验 SHA-256：`cloudflared 2026.9.3`、`xcbeautify 3.2.1`、`SwiftLint 0.65.1`、`SwiftFormat 0.63.0`。

## 常见问题

**实时预览失败：`Set AGENT_PREVIEW_PASSWORD ...`**
App 仓库没有配置该 Secret，或入口文件没有把它传给可复用工作流。

**实时预览没有启动**
只有 `workflow_dispatch` 手动触发且 `live_preview=true` 时才会启动，push/PR 不会。

**预览地址打不开**
job 结束后地址即失效；请在 job 仍在运行时打开。Quick Tunnel 反复 DNS 失败时改用 [固定域名 Named Tunnel](#b-实时预览固定域名-named-tunnel可选)。

**`Set both AGENT_PREVIEW_URL variable and AGENT_PREVIEW_TUNNEL_TOKEN secret`**
固定域名的两项必须同时配置，或同时删除以回到 Quick Tunnel。

**`ui-tree.json` 为空或报错**
iOS 26 上 AXe 偶尔丢失 bridge，工作流会自动重试 3 次；失败时仅警告，不影响测试结果。

**`Requested iOS runtime not installed`**
runner 镜像上没有该 iOS 版本，改用已安装的 `ios_runtime`。

**TestFlight 导出签名失败**
检查 API Key 角色是否有权限管理证书/描述文件、`APPLE_TEAM_ID` 是否正确、App 是否已在 App Store Connect 创建、Bundle ID 能力是否与 entitlements 一致。

**测试报告里的快照全部失败**
先看报告开头的模拟器：请求的机型不存在时 CI 会换成别的机型并给出警告，参考图就对不上。改回存在的机型，或确认后用 `record_snapshots` 重新录制。

**无障碍审计失败但 CI 是绿的**
`accessibility_audit` 默认是 `warn`，只警告不阻断；问题清干净后改成 `fail`。

**发版门槛报 `No green ios-build.yml run`**
这个提交的 Build & Test 没有通过，或者还没跑过（例如直接在未经 CI 的提交上打了标签）。先让它变绿再发版。报 `Cannot read ... runs` 时，入口文件缺 `actions: read`。

**build number 冲突**
默认使用 `GITHUB_RUN_NUMBER`；如果之前上传过更大的号，手动运行时指定 `build_number`。

---

## 致谢与开源许可

本仓库以 [MIT License](LICENSE) 开源。

CI 中直接运行的开源工具（固定版本，运行时下载，不包含在本仓库中）：

- [XcodeBuildMCP](https://github.com/getsentry/XcodeBuildMCP)（MIT）：Simulator 无障碍 UI 树
- [serve-sim](https://github.com/EvanBacon/serve-sim)（Apache-2.0）：Simulator 画面串流与 HID 触控
- [icon-composer-mcp](https://github.com/ethbak/icon-composer-mcp)（MIT）：`.icon` Liquid Glass 图标在 6 种外观模式下的预览渲染
- [cloudflared](https://github.com/cloudflare/cloudflared)（Apache-2.0）：实时预览隧道
- [xcbeautify](https://github.com/cpisciotta/xcbeautify)（MIT）：整理 xcodebuild 日志
- [SwiftLint](https://github.com/realm/SwiftLint)（MIT）、[SwiftFormat](https://github.com/nicklockwood/SwiftFormat)（MIT）：静态检查

推荐 App 在测试里使用（App 自己的依赖，不由本仓库运行）：[swift-snapshot-testing](https://github.com/pointfreeco/swift-snapshot-testing)（快照测试）、[swift-dependencies](https://github.com/pointfreeco/swift-dependencies)（控制“今天”等依赖）。

设计参考（未复制代码）：

- [native-sim](https://github.com/bidah/native-sim)：GitHub → macOS runner → Simulator → serve-sim → 鉴权网关 → Cloudflare Tunnel → 浏览器 的整体思路；本仓库针对原生 Swift/Xcode 项目独立实现了密码网关、接口白名单、shell 隔离和公网自检
- [Maestro](https://github.com/mobile-dev-inc/Maestro)：评估后不采用，关键流程由 XCUITest 负责（结果直接进 `.xcresult`，不需要 Java）

包含的第三方代码：`cloudbase-mcp-gateway/` 中的 OAuth 辅助文件来自 Cloudflare 的 [remote-mcp-github-oauth](https://github.com/cloudflare/ai/tree/main/demos/remote-mcp-github-oauth) 示例（MIT）。完整清单与许可文本见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

## 完整工作流图

![完整工作流](docs/images/workflow-detailed.png)

> 图中“GitHub Secrets”一栏列出的 `.p12` 证书和 Provisioning Profile 是概念示意；当前工作流通过 App Store Connect API Key 自动签名，实际需要的 Secrets 以 [Secrets 与 Variables 一览](#secrets-与-variables-一览) 为准。
