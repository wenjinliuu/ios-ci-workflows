# 日常：改代码、写测试、读报告

## 循环

1. 改代码，同时补测试（规则见 [SKILL.md](SKILL.md)）。
2. push 或开 PR，等 **Build & Test** 跑完。
3. 读测试报告，按报告修，再 push。

`.ios-ci.yml` 配了快线和慢线（`build_test.fast_test_plan`、`full_test_plan`）时，每次跑的范围不同：

| 什么时候 | 跑什么 | 报告开头的“范围” |
| --- | --- | --- |
| PR 和分支上的每次 push | 快线：编译 + 逻辑 + 迁移 + 快照 | 快线 |
| 合并到 main 后 | 慢线：只跑 UI 关键流程和无障碍审计 | 慢线 |
| 手动运行 Build & Test | 自己选 `fast` / `ui` / `full` | 按所选 |

- PR 上是绿的，不代表 UI 流程没问题：**改了界面交互、关键流程或 UI 测试，合并前在工作分支上手动跑一次 `ui`（或 `full`）**，不要等合并后在 main 上才发现。
- main 上的慢线红了：马上开一个修复 PR，同样先手动跑 `ui` 确认；这时候不要发版。
- 同一个分支上，新的运行会取消还在跑的旧运行；手动运行也算在内，所以一个分支上一次只跑一种范围，等上一个跑完再开下一个。
- 只改 `*.md` 和 `docs/**` 的提交不跑 Build & Test。

## 测试报告在哪

- 运行页面的 job summary（“测试报告”一节）
- 产物 `build-test-<run>`：
  - `report/report.md`、`report/report.json`：结论、失败的测试和原因、快照不一致、无障碍问题、新录制的快照
  - `report/attachments/`：失败测试的附件；快照失败时有 reference / failure / difference 三张图
  - `xcodebuild.log`：完整编译测试日志；`Test.xcresult`
  - `launch.png`、`app.log`：App 启动后的截图、日志
  - `ui-tree.json`：无障碍 UI 树；快线不抓，只有慢线和全部测试的运行里才有

下载不了产物时，只读 job summary 和 job 日志就够了。

报告开头的“结论”就是 CI 的判定：通过 / 未通过 / 通过（N 个无障碍警告）。`report.json` 里每个失败有 `kind`：

| kind | 含义 | 是否让 CI 变红 |
| --- | --- | --- |
| `test` | 逻辑测试、迁移测试、关键流程（XCUITest）失败 | 是 |
| `snapshot` | 快照与参考图不一致，或刚录制了新参考图 | 是（录制模式下不算） |
| `accessibility` | 无障碍审计的失败：失败信息以 “Accessibility audit” 开头，或测试名带 Accessibility | `.ios-ci.yml` 里 `accessibility_audit: warn` 时只警告，`fail` 时阻断 |

编译失败时报告只列 `xcodebuild.log` 里的 `error:` 行。

## 写测试

写测试时遵守 [testing.md](testing.md) 的几条约束。下面是各层在这套 CI 里的具体写法。

| 层 | 写法 |
| --- | --- |
| 逻辑测试 | Swift Testing（或 XCTest）；同类情况用参数化测试合并；“现在”作为参数传入，测试里传固定时间 |
| 迁移测试 | 加载 `Fixtures/` 里每个历史版本的数据文件，检查读出来的内容；每发一个正式版加一份数据 |
| 快照测试 | swift-snapshot-testing，固定日期和示例数据，参考图在 `__Snapshots__` |
| 关键流程 | XCUITest，用示例数据启动，不读写用户数据；只写核心用户路径 |
| 无障碍审计 | 写在关键流程里：流程走到哪一页，就在那一页调用 `performAccessibilityAudit()`，不为每个页面单独启动 App；每个主要页面至少被一条流程走到并审计一次 |

无障碍审计的写法：在审计的问题处理闭包里用 `XCTFail("Accessibility audit（页面名）：问题 — 元素")` 记录每个问题并返回 `true`，失败信息以 “Accessibility audit” 开头，CI 才能把它归为无障碍问题；写上元素的标签和位置，报告里就能直接定位。元素多的页面在慢 runner 上审计可能超时（“Audit failed to complete in time”）：先把问题收集起来、审计完成后再逐条 `XCTFail`，超时就重跑一次，这样重跑不会把同一个问题记两遍（样例见 CalenEase 的 `KeyFlowTests.auditAccessibility`）。新加一个页面或弹窗时，让某条关键流程走到它并审计。

写 XCUITest 前先看最近一次慢线或全部测试报告里的 `ui-tree.json`：里面是真实界面的元素、标签和层级，按它写查询，不要猜。快线的报告里没有它，需要时手动跑一次 `ui`。

新测试放哪一份计划：逻辑、迁移、快照测试所在的 target 同时在快线和全部计划里；UI 测试 target 只在全部计划里，由慢线跑。新建测试 target 时要把它加进对应的计划。

App 接了后端时，测试里把后端模拟掉，专门测网络失败、超时、返回格式异常，不依赖真实服务器。

## 有意改了界面：重录快照

1. 在工作分支上手动运行 Build & Test，范围选 `fast`（快照在快线里；`ui` 不跑快照），勾选 `record_snapshots`。
2. `.ios-ci.yml` 里 `build_test.commit_recorded_snapshots: true` 时，CI 把新参考图直接提交回这个分支；否则下载产物 `recorded-snapshots-<run>` 按原路径提交。
3. 机器人的提交不会触发新运行：再手动跑一次 Build & Test，确认变绿。
4. 在 PR 里写清改了哪些页面。参考图只在 CI 上生成，不在本地录。

快照对机型和系统版本敏感。报告开头写着这次用的模拟器；CI 报“runner 上没有这个模拟器”时，按报错里的列表改 `.ios-ci.yml` 的 `toolchain`，再重录快照。

## 想亲眼看界面

手动运行 **Live Preview**，在运行中的 job 日志或 summary 里拿到地址交给用户，用户用预览密码登录。它是给人看的，不是测试；你在操作模拟器时，提醒用户只看不点。
