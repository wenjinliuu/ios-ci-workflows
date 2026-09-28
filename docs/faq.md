# 常见问题

**`.ios-ci.yml：...`**
配置文件写错了，报错会说是哪一项：缺必填键、拼错键名、版本号没加引号等。对照 [config.md](config.md) 改。

**`runner 上没有 iPhone 17 Pro (iOS 26.4)`**
runner 镜像升级了，固定的模拟器不在了。报错下面列着 runner 上有的机型和版本，改 `.ios-ci.yml` 的 `toolchain`，再用 `record_snapshots` 重录快照。

**`This runner does not report job.workflow_repository / job.workflow_sha`**
工作流靠这两个值找到自己的脚本。GitHub 托管的 runner 都支持；自托管 runner 请升级 runner 版本。

**测试报告里的快照全部失败**
先看报告开头的模拟器和版本是不是和录制时一样。换了 Xcode、机型或 iOS 版本后要重录快照。

**无障碍审计失败但 CI 是绿的**
`accessibility_audit` 默认 `warn`，只警告不阻断；问题清干净后改成 `fail`。

**录制快照后 CI 没有再跑**
用任务令牌推送的提交不会触发新运行，手动再跑一次 Build & Test。提交失败报 `grant 'contents: write'` 时，入口文件缺这个权限。

**`ui-tree.json` 为空或报错**
iOS 26 上 AXe 偶尔丢失 bridge，工作流会自动重试 3 次；失败只警告，不影响测试结果。

**Live Preview 报 `Set AGENT_PREVIEW_PASSWORD`**
App 仓库没配这个 Secret，或它短于 12 位，或入口文件没把它传下去。

**预览地址打不开**
job 结束后地址即失效，请在 job 还在运行时打开。Quick Tunnel 反复解析失败时改用[固定域名](live-preview.md#可选固定域名-named-tunnel)。

**`Set both the AGENT_PREVIEW_URL variable and the AGENT_PREVIEW_TUNNEL_TOKEN secret`**
固定域名的两项必须同时配置，或同时删除以回到 Quick Tunnel。

**TestFlight 没有上传，test 那一步红了**
发版前会完整跑一次 Build & Test，没通过就不签名。先按测试报告修好。

**TestFlight 导出签名失败**
检查 API Key 角色是否有权限管理证书和描述文件、`APPLE_TEAM_ID` 是否正确、App 是否已在 App Store Connect 创建、Bundle ID 的能力是否和 entitlements 一致。

**build number 冲突**
默认用 `GITHUB_RUN_NUMBER`；之前上传过更大的号时，手动运行并指定 `build_number`。

**开验收 Issue 报 `grant 'issues: write'`**
入口文件缺这个权限，或者把 `testflight.acceptance_issue` 改成 `false`。
