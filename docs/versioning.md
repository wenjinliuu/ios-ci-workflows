# 版本与升级

## 本仓库怎么发版

- 打语义化标签（如 `v1.0.0`）并建 Release 写更新说明；同时维护大版本标签 `v1`，每次发 `v1.x.x` 时把它移到最新提交。
- 发版后 `main` 照常开发；只有移动 `v1` 标签才会影响引用 `@v1` 的人。
- 改了输入参数或配置文件的键，导致使用者的入口文件或 `.ios-ci.yml` 要跟着改，就升 `v2`，`v1` 留在原地不动。

## 使用者怎么引用

| 写法 | 特点 |
| --- | --- |
| `@<SHA> # v1.0.0` | 推荐。锁死不变；Dependabot 能识别注释里的版本并提升级 PR |
| `@v1` | 省事，自动拿到 v1 里的修复 |
| `@main` | 不要用：本仓库任何一次合并都会立刻改变你的 CI |

也可以 fork 后引用自己的 fork。脚本和网关代码从 `uses:` 指向的同一个仓库、同一个提交拉取，所以只需要写一次 `@<SHA>`，fork 后也自动用 fork 里的脚本。

在 App 仓库加 `.github/dependabot.yml` 让它提升级 PR：

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

## 升级步骤

1. 看本仓库 Release 的更新说明，有没有要改 `.ios-ci.yml` 的地方。
2. 把 App 仓库所有入口文件里的 `@<旧SHA>` 改成同一个新 SHA（和版本注释）。
3. 手动跑一次 Build & Test 和 TestFlight 的 `dry_run` 确认无误。

修改签名、描述文件或上传相关步骤前，先仔细看现有 TestFlight 运行的输出。

## 外部依赖

本仓库只做编排，工具在运行时下载，不放进仓库：

| 来源 | 内容 | 固定方式 |
| --- | --- | --- |
| runner 镜像 | Xcode、模拟器、Node | 固定 `macos-26`；`.ios-ci.yml` 显式写 Xcode、机型、iOS 版本 |
| npm | xcodebuildmcp、serve-sim、icon-composer-mcp | 固定版本号 |
| 二进制下载 | cloudflared、xcbeautify、SwiftLint、SwiftFormat、XcodeGen | 固定版本 + 校验 SHA-256 |
| Swift 包（App 仓库） | swift-snapshot-testing、swift-dependencies 等 | `Package.resolved` 锁定 |

上游删版本或服务故障会导致 CI 失败；runner 镜像更新会改变 Xcode 和模拟器版本，快照测试最敏感。所以版本都固定、下载都校验哈希，找不到固定的模拟器就直接失败，而不是悄悄换一个。
