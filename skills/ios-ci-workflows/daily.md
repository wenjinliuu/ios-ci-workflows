# 日常：改代码、写测试、读报告

## 循环

1. 改代码，同时补测试（规则见 [SKILL.md](SKILL.md)）。
2. push 或开 PR，等 **Build & Test** 跑完。
3. 读测试报告，按报告修，再 push。

## 测试报告在哪

- 运行页面的 job summary（“测试报告”一节）
- 产物 `build-test-<run>`：
  - `report/report.md`、`report/report.json`：结论、失败的测试和原因、快照不一致、无障碍问题、新录制的快照
  - `report/attachments/`：失败测试的附件；快照失败时有 reference / failure / difference 三张图
  - `xcodebuild.log`：完整编译测试日志；`Test.xcresult`
  - `launch.png`、`ui-tree.json`、`app.log`：App 启动后的截图、无障碍 UI 树、日志

下载不了产物时，只读 job summary 和 job 日志就够了。

报告开头的“结论”就是 CI 的判定：通过 / 未通过 / 通过（N 个无障碍警告）。`report.json` 里每个失败有 `kind`：

| kind | 含义 | 是否让 CI 变红 |
| --- | --- | --- |
| `test` | 逻辑测试、迁移测试、关键流程（XCUITest）失败 | 是 |
| `snapshot` | 快照与参考图不一致，或刚录制了新参考图 | 是（录制模式下不算） |
| `accessibility` | 测试名匹配 Accessibility 的失败，即无障碍审计 | `.ios-ci.yml` 里 `accessibility_audit: warn` 时只警告 |

编译失败时报告只列 `xcodebuild.log` 里的 `error:` 行。

## 写测试

| 层 | 写法 | 数量 |
| --- | --- | --- |
| 逻辑测试 | Swift Testing（或 XCTest）；边界日期用参数化测试一次覆盖；用 swift-dependencies 固定“今天” | 最多 |
| 迁移测试 | 加载 `Fixtures/` 里每个历史版本的数据文件，检查读出来的内容 | 每发一个正式版加一份数据 |
| 快照测试 | swift-snapshot-testing，固定日期和示例数据，参考图在 `__Snapshots__` | 关键组件和页面 |
| 关键流程 | XCUITest，用示例数据启动，不读写用户数据 | 只写 3～5 条 |
| 无障碍审计 | XCUITest 里调 `performAccessibilityAudit()`，测试名带 Accessibility，每个页面一个测试 | 每个主页面一个 |

写 XCUITest 前先看最近一次报告里的 `ui-tree.json`：里面是真实界面的元素、标签和层级，按它写查询，不要猜。

App 接了后端时，测试里把后端模拟掉，专门测网络失败、超时、返回格式异常，不依赖真实服务器。

## 有意改了界面：重录快照

1. 在工作分支上手动运行 Build & Test，勾选 `record_snapshots`。
2. `.ios-ci.yml` 里 `build_test.commit_recorded_snapshots: true` 时，CI 把新参考图直接提交回这个分支；否则下载产物 `recorded-snapshots-<run>` 按原路径提交。
3. 机器人的提交不会触发新运行：再手动跑一次 Build & Test，确认变绿。
4. 在 PR 里写清改了哪些页面。参考图只在 CI 上生成，不在本地录。

快照对机型和系统版本敏感。报告开头写着这次用的模拟器；CI 报“runner 上没有这个模拟器”时，按报错里的列表改 `.ios-ci.yml` 的 `toolchain`，再重录快照。

## 想亲眼看界面

手动运行 **Live Preview**，在运行中的 job 日志或 summary 里拿到地址交给用户，用户用预览密码登录。它是给人看的，不是测试；你在操作模拟器时，提醒用户只看不点。
