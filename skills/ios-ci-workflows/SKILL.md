---
name: ios-ci-workflows
description: 在接入了 wenjinliuu/ios-ci-workflows 的 iOS App 仓库里改代码、写测试、读 CI 测试报告、录制快照、发 TestFlight 时使用。说明三条可复用工作流怎么调用，CI 报告怎么读，以及改代码时必须遵守的测试规则。
---

# ios-ci-workflows

这个仓库给 iOS App 提供三条可复用工作流。App 仓库只放 App 代码、测试和三个很薄的入口文件；编译、测试、报告、签名上传都在 GitHub Actions 的 macOS runner 上完成，本地不需要 Mac。

| App 仓库里的入口 | 调用 | 做什么 |
| --- | --- | --- |
| `icon-preview.yml` | `app-icon.yml` | 生成并校验 Liquid Glass 图标，渲染预览图 |
| `ios-build.yml` | `agent-preview.yml` | 编译、跑全部测试、写测试报告；可选实时串流预览 |
| `testflight.yml` | `testflight-release.yml` | 发版门槛、核对 Apple 注册、签名上传、开验收 Issue |

入口文件的写法见本仓库 README 的“接入步骤”，三个文件里的 `@<SHA>` 和 `ci_revision` 必须是同一个提交。

## 改代码的循环

1. 改代码，同时补测试（规则见下）。
2. 推送或开 PR，等 **Build & Test** 跑完。
3. 读测试报告，按报告修，再推送。

测试报告在两个地方，内容一样：

- 运行页面的 job summary（“测试报告”一节）
- 产物 `agent-preview-<run>`：
  - `report/report.md`、`report/report.json`：结果、失败的测试和原因、快照不一致、无障碍问题、新录制的快照
  - `report/attachments/`：失败测试带的附件；快照失败时有 reference / failure / difference 三张图
  - `xcodebuild.log`：完整编译测试日志
  - `launch.png`、`ui-tree.json`、`app.log`：App 启动后的截图、无障碍 UI 树、日志

`report.json` 里每个失败有 `kind`：

| kind | 含义 | 是否让 CI 变红 |
| --- | --- | --- |
| `test` | 逻辑测试、关键流程（XCUITest）失败 | 是 |
| `snapshot` | 快照与参考图不一致，或刚录制了新参考图 | 是（录制模式下不算） |
| `accessibility` | 测试名匹配 `accessibility_test_pattern`（默认含 Accessibility）的失败，即无障碍审计 | 默认只警告；`accessibility_audit: fail` 后变红 |

编译失败时报告只列 `xcodebuild.log` 里的 `error:` 行。

## 测试规则

- **新功能必须带逻辑测试。** 逻辑测试最多、最便宜：排班、日期、数据存取这类规则都写成 Swift Testing 或 XCTest，边界日期用参数化测试一次覆盖。
- **测试是累积的。** 改哪个功能就补哪个功能的测试，每次 CI 都把全部测试从头跑一遍。
- **改界面要走快照录制。** 有意改了界面时，在工作分支上手动运行 Build & Test 并勾选 `record_snapshots`。入口文件打开了 `commit_recorded_snapshots` 时，CI 会把新参考图直接提交回这个分支；否则下载产物 `recorded-snapshots-<run>`，按原路径提交。之后再手动跑一次 Build & Test（机器人的提交不会自动触发），确认变绿，并在 PR 里写清改了哪些页面。参考图只在 CI 上生成，不在本地录制。
- **关键流程只写 3～5 条 XCUITest**，覆盖最核心的路径；无障碍审计在 XCUITest 里调用 `performAccessibilityAudit()`，测试名里带 Accessibility。
- **删测试、改断言的预期值必须写明理由。** 不能为了让 CI 变绿而改测试。
- 快照对机型和系统版本敏感。报告开头写着这次用的模拟器；如果 CI 提示请求的机型不存在、换成了别的机型，快照失败可能只是机型不同，先确认再改代码。

## 发版

- 手动运行 **TestFlight**，或推送 `v*` 标签。
- 先勾 `lookup_only` 核对 Bundle ID 和 App 已在 Apple 注册；再勾 `dry_run` 确认能打包。
- 设置了 `build_workflow` 时，只有这个提交的 Build & Test 是绿的才会发版（还在跑会等最多 `build_wait_minutes` 分钟）。
- 开了 `acceptance_issue` 时，上传成功后会开一个“发版验收”Issue：固定项来自 `.github/release-checklist.md`，本次项来自 `.github/release-checklist-current.md`。发版前把针对这次改动要在真机上看的项写进后者；测试员在 Issue 里打勾、评论，下次读这个 Issue 修问题。

## 实时串流预览

手动运行 Build & Test 并勾选 `live_preview`，job 日志和 summary 里会给出一个预览地址，用仓库的预览密码登录后可以在浏览器里看画面、点击、输入。它是给人调 UI、复现 bug 用的，不是测试；AI 验证改动靠测试报告。

## 不要做的事

- 不要引用中央仓库的 `@main`，用固定的提交或版本标签。
- 不要在工作流 YAML、日志或提交里写明文密钥；密钥只在 App 仓库的 Secrets 里。
- 不要把测试挪到 CI 以外的地方跑来“证明”通过；以 CI 报告为准。
