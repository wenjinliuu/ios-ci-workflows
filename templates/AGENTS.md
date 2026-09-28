# AI 协作规则

- 本项目用 [ios-ci-workflows](https://github.com/wenjinliuu/ios-ci-workflows) 编译和测试；本地不跑 Xcode。改完代码 push，读 Build & Test 的测试报告再修。
- 新功能必须带测试；删测试、改断言的预期值必须在提交里写明理由。
- 维护测试时遵循 ios-ci-workflows 技能里的 testing 原则（skills/ios-ci-workflows/testing.md）：放在最便宜的一层、先改后加、只按删除规则删；增删测试时同步更新仓库根目录的 TESTING.md。
- 有意改了界面：手动运行 Build & Test 并勾选 record_snapshots，再跑一次确认变绿，并说明改了哪些页面。
- PR 上只跑快线（逻辑、迁移、快照）；改了界面交互、关键流程或 UI 测试时，合并前手动跑一次 Build & Test 的 ui（或 full）。
- 涉及 CloudBase 时，先执行 `npx skills add tencentcloudbase/cloudbase-skills` 并读取 cloudbase-guidelines。
- 部署只走 git → CI；MCP 只用来查数据、看日志、排查问题；AI 默认只连测试环境。
- 更多细节见 ios-ci-workflows 的 Skill：skills/ios-ci-workflows/SKILL.md。
