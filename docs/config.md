# 配置文件 `.ios-ci.yml`

App 仓库根目录的 `.ios-ci.yml` 保存 App 的全部设置，所有工作流都从这里读，入口文件里只剩 `uses:`、`secrets:` 和每次运行时才决定的开关。模板见 [`templates/.ios-ci.yml`](../templates/.ios-ci.yml)。

每条工作流的第一个 job（`config`）读这个文件，补默认值、校验，再交给后面的 job。写错了（缺必填键、拼错键名、版本号没加引号）会在这一步直接失败，并说明是哪一项。

配置文件放在别处时，给入口文件的 `with:` 加 `config: path/to/ios-ci.yml`。

## 顶层：工程

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `project` | 必填 | `.xcodeproj` 路径，相对 `workdir` |
| `scheme` | 必填 | 主 App scheme，包含测试 target |
| `bundle_id` | 必填 | 校验构建产物、启动 App、核对 Apple 注册 |
| `workdir` | `.` | 工程所在目录，相对仓库根 |
| `display_name` | `''` | 填了会在发版时核对 `CFBundleDisplayName`，也用作验收 Issue 标题 |
| `sync_command` | `true` | 把 SVG 图层同步进 `.icon` 的命令，在 `workdir` 里运行 |
| `generate_command` | `true` | 生成工程的命令，如 `xcodegen generate`；含 `xcodegen` 时自动安装固定版本的 XcodeGen（2.46.0，校验 SHA-256）。发版时会带上 `DEVELOPMENT_TEAM` 环境变量 |
| `icon_path` | `''` | `.icon` 图标包路径，相对 `workdir`；用 App Icon 工作流时必填 |

## `toolchain`：工具链

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `xcode` | `'26.6'` | Xcode 版本 |
| `simulator` | `iPhone 17 Pro` | 模拟器机型 |
| `ios` | `'26.4'` | iOS 版本，写到小版本；同一小版本的补丁运行时（26.4.1）也算 |

三项都显式固定：快照参考图只在同一 Xcode、机型、iOS 版本上可比。版本号要加引号，否则 YAML 会把 `26.10` 读成 `26.1`。runner 镜像升级后如果没有这个机型或版本，CI 直接失败并列出 runner 上有的，不会悄悄换成别的；按列表改这里，再重录快照。

## `build_test`：Build & Test

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `test_plan` | `''` | `.xctestplan` 名；空则跑 scheme 默认的测试。没配下面两份计划时用它 |
| `fast_test_plan` | `''` | 快线的测试计划（逻辑 + 迁移 + 快照，不含 UI 测试） |
| `full_test_plan` | `''` | 全部测试的计划；慢线也在它里面挑 UI 测试 target 跑 |
| `ui_test_target` | `''` | UI 测试 target 名（关键流程 + 无障碍审计），慢线只跑它 |
| `accessibility_audit` | `warn` | `warn` 只警告；`fail` 让无障碍问题阻断 CI |
| `accessibility_test_pattern` | `(?i)accessibility` | 匹配测试名的正则，命中的失败算无障碍问题 |
| `commit_recorded_snapshots` | `false` | 录制快照后由 CI 把参考图提交回运行的分支；入口文件要给 `contents: write` |

### 快线与慢线

`fast_test_plan` 和 `full_test_plan` 都写了，Build & Test 就按触发方式自动选范围，不按改了什么挑测试：

| 触发 | 范围（`suite`） | 跑什么 |
| --- | --- | --- |
| PR、分支上的推送 | `fast` | 快线计划 |
| 推送到默认分支（合并到 main） | `ui` | 全部计划里只跑 `ui_test_target` |
| 手动运行 | 入口文件传入的 `suite`，没传就是 `fast` | |
| TestFlight 门槛 | 复用这个提交已通过的 `fast` + `ui`，查不到才跑 `full` | |

两份计划都没写时，每次都跑 `test_plan` 或 scheme 的全部测试，和以前一样。

两份计划都建议把测试附件（录屏、截图）设为**测试成功即删除**（`systemAttachmentLifetime` / `userAttachmentLifetime` 为 `deleteOnSuccess`），产物只保留失败的附件。

## `app_icon`：App Icon

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `commit_previews` | `false` | 把 7 张预览图和一个图片表格 README 提交回仓库；入口文件要给 `contents: write` |
| `previews_dir` | `DesignAssets/AppIcon/previews` | 预览图目录，相对仓库根；入口文件的 `paths` 要排除它 |

## `testflight`：TestFlight

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `entitlement_mode` | `none` | `none` 不嵌入；`required` 必须嵌入成功；`best-effort` 失败不阻塞；`icloud-verified` 只有 App ID 确实勾选了 iCloud 容器时才嵌入 |
| `entitlements_path` | `''` | entitlements 文件，相对 `workdir`；`entitlement_mode` 不是 `none` 时必填 |
| `icloud_container` | `''` | 如 `iCloud.com.example.app`；`icloud-verified` 时必填 |
| `expected_team_id` | `''` | 填了会核对 `APPLE_TEAM_ID`，防止传错团队 |
| `artifact_prefix` | `''` | dSYM 产物名前缀 |
| `inspect_icloud` | `false` | 额外导出一份本地包，输出实际的 entitlement 报告 |
| `acceptance_issue` | `false` | 上传成功后开“发版验收”Issue；入口文件要给 `issues: write` |
| `acceptance_checklist` | `.github/release-checklist.md` | 验收 Issue 的固定项 |
| `acceptance_extra` | `.github/release-checklist-current.md` | 验收 Issue 的本次项，AI 按这次改动写 |

用了 iCloud 的 App 统一用 `icloud-verified`：App ID 上确实勾选了该容器才嵌入 iCloud 权限；否则（包括首次发布还没有描述文件可查）跳过并警告，照常上传，App 应把数据退回存到本机。

## 完整示例

```yaml
workdir: ios
project: CalenEase.xcodeproj
scheme: CalenEase
bundle_id: com.wenjinliu.calenease
display_name: 省心日历
sync_command: bash Scripts/sync-app-icon.sh
generate_command: xcodegen generate
icon_path: CalenEase/Resources/AppIcon.icon

toolchain:
  xcode: '26.6'
  simulator: iPhone 17 Pro
  ios: '26.4'

build_test:
  commit_recorded_snapshots: true

testflight:
  entitlement_mode: icloud-verified
  entitlements_path: CalenEase/Resources/CalenEase.entitlements
  icloud_container: iCloud.com.wenjinliu.calenease
  artifact_prefix: calenease-
  acceptance_issue: true
```
