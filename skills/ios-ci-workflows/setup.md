# 接入一个 App 仓库

目标：App 仓库里有 `.ios-ci.yml`、入口文件、`AGENTS.md`，push 后 Build & Test 能出测试报告。模板都在中央仓库的 `templates/`。

## 1. 先弄清工程

在 App 仓库里找：

- `.xcodeproj` 或 XcodeGen 的 `project.yml`，以及它所在的目录（`workdir`）
- 主 App scheme、Bundle ID、显示名
- 有没有测试 target；scheme 的 test action 里要包含它们
- `.icon` 图标包（含 `icon.json`）和同步 SVG 图层的脚本
- entitlements 文件，是否用 iCloud（容器 ID）

不支持：macOS / watchOS 目标、一个仓库多个 App。遇到就告诉用户，不要硬接。

## 2. 写 `.ios-ci.yml`

从 `templates/.ios-ci.yml` 复制到仓库根目录，只填需要的键，其余删掉用默认值。键的含义见中央仓库 `docs/config.md`。要点：

- `project`、`scheme`、`bundle_id` 必填。
- `toolchain` 的版本号要加引号。
- 用 XcodeGen 时 `generate_command: xcodegen generate`；已提交 `.xcodeproj` 时写 `'true'`。
- 用 iCloud 时 `testflight.entitlement_mode: icloud-verified` 并填 `icloud_container`。
- 刚接入时不用拆快线和慢线，每次跑全部测试。等 UI 测试让一次 Build & Test 超过 10 分钟左右，再拆：
  1. 复制 `templates/Fast.xctestplan`（逻辑 + 迁移 + 快照 target）和 `templates/Full.xctestplan`（全部 target）到 `.xcodeproj` 所在目录，把 `MyApp` 换成真实的 target 名，把两份计划挂到 scheme 的 test action（XcodeGen：`schemes.<名>.test.testPlans`）。
  2. 用 XcodeGen 时，复制 `templates/Scripts/sync-test-plans.py`，并把生成命令写成 `xcodegen generate && python3 Scripts/sync-test-plans.py`，它会把 target ID 填进两份计划。
  3. 在 `.ios-ci.yml` 的 `build_test` 下写 `fast_test_plan`、`full_test_plan`、`ui_test_target`。
  4. 把无障碍审计并进关键流程（写法见 [daily.md](daily.md)）。

## 3. 选等级，复制入口文件

| 等级 | 复制 | 用户要配的 Secrets |
| --- | --- | --- |
| 1 Build & Test | `.github/workflows/build-test.yml` | 无 |
| 2 + TestFlight | `.github/workflows/testflight.yml`、`.github/release-checklist.md` | `APPLE_TEAM_ID`、`APP_STORE_CONNECT_KEY_ID`、`APP_STORE_CONNECT_ISSUER_ID`、`APP_STORE_CONNECT_PRIVATE_KEY` |
| 3 + Live Preview | `.github/workflows/live-preview.yml` | `AGENT_PREVIEW_PASSWORD`（≥12 位） |
| 4 + App Icon | `.github/workflows/app-icon.yml`（改 `paths` 为图标素材路径） | 无 |

- 所有入口文件的 `@<SHA>` 填同一个：中央仓库最新 Release 的提交，后面加 `# v1.x.x` 注释。
- 入口文件的 `permissions` 按用到的功能给：录快照提交回分支、提交图标预览要 `contents: write`，验收 Issue 要 `issues: write`，TestFlight 复用已有测试结果要 `actions: read` 和 `pull-requests: read`；不用就去掉。
- Secrets 只能由用户在 GitHub 网页上添加（Settings → Secrets and variables → Actions）。把要加哪几项、从哪里来（中央仓库 `docs/secrets.md`）告诉用户，不要让用户把密钥发给你。

## 4. `AGENTS.md`

把 `templates/AGENTS.md` 复制到 App 仓库根目录（已有就把那几条合并进去）。用 Claude 的仓库可以再放一个内容相同的 `CLAUDE.md`。

## 5. 验证

1. push → Build & Test 的 summary 里有“测试报告”。拆了快线和慢线的，再手动跑一次 `ui` 和一次 `full`，确认 UI 流程和审计都通过。
2. 第一次有快照测试时，手动运行 Build & Test 并勾选 `record_snapshots` 录参考图，再跑一次确认变绿。
3. 接了 TestFlight：手动运行并勾选 `lookup_only` 核对 Apple 注册；再勾 `dry_run` 确认测试门槛和打包都通过。
4. 接了 Live Preview：手动运行，在 job 日志里拿地址交给用户。
