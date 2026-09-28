# 发版：TestFlight 与验收

## 发版

- 推送 `v*` 标签（如 `v1.2.0`），或手动运行 **TestFlight**。
- 流程：verify（核对 Apple 注册）→ test（完整跑一次 Build & Test，没通过就不签名）→ release（签名上传）→ acceptance（开验收 Issue）。
- 第一次接入或 Apple 侧有改动时：先勾 `lookup_only` 核对 Bundle ID 和 App 已注册；再勾 `dry_run` 确认测试门槛和打包都能过。
- build number 冲突时手动运行并指定 `build_number`；版本号用 `marketing_version`。

## 验收清单

`.ios-ci.yml` 里 `testflight.acceptance_issue: true` 时，上传成功后会开一个“发版验收”Issue：

- **固定项**来自 `.github/release-checklist.md`：每次都要在真机上看的事（覆盖升级旧数据还在、提醒、iCloud、滑动流畅、深色和大字号、断网不崩）。
- **本次项**来自 `.github/release-checklist-current.md`：发版前由你按这次改动写，比如改了农历计算就加“核对下个月农历和节气”。

测试员在 Issue 里打勾、评论、配截图。下次开工先读最近的验收 Issue，按评论修问题；反复出现的问题加进固定项。

## 迁移测试

每发一个正式版，把这个版本生成的样例数据文件（如 `v1.0-sample.store`）存进测试的 `Fixtures/`，加一个测试用新代码读它并检查内容。用 iCloud 同步时还要想到新旧两个版本同时同步同一份数据。

## 上线后

崩溃监控：苹果的 MetricKit 和 Xcode 崩溃报告免费但反馈慢；上 TestFlight 后再接 Sentry。CI 全绿只代表“写了的测试都过了”，只覆盖一台模拟器、一个 iOS 版本。
