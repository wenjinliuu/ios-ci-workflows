---
name: ios-ci-workflows
description: 在用 wenjinliuu/ios-ci-workflows 的 iOS App 仓库里接入 CI、改代码、写测试、读测试报告、录制快照、开实时预览、发 TestFlight 时使用。说明该读哪一页、CI 报告怎么读，以及改代码时必须遵守的测试规则。
---

# ios-ci-workflows

App 仓库只放 App 代码、测试、一个配置文件 `.ios-ci.yml` 和几个很薄的入口文件；编译、测试、报告、签名上传都在 GitHub Actions 上完成，本地不需要 Mac，也不在本地跑 Xcode。

## 先看哪一页

| 情况 | 读 |
| --- | --- |
| 这个仓库还没接入（没有 `.ios-ci.yml`） | [setup.md](setup.md) |
| 改代码、修 bug、写测试、读报告、录快照、开实时预览 | [daily.md](daily.md) |
| 发 TestFlight、处理验收 Issue | [release.md](release.md) |
| 操作后端、写云函数 | 官方 CloudBase 技能（用到时执行 `npx skills add tencentcloudbase/cloudbase-skills`，读 cloudbase-guidelines）+ 本仓库 [docs/cloudbase.md](../../docs/cloudbase.md) |
| 编译、跑测试、看界面结构 | 交给 CI；只读测试报告和 `ui-tree.json` |

和其他技能或文档冲突时，以本 Skill 为准，尤其是“部署只走 CI”。

## 必须遵守

- **CI 是唯一的测试入口。** 改完 push，读 Build & Test 的报告再修；不要把测试挪到 CI 以外的地方跑来“证明”通过。
- **新功能必须带测试。** 改哪个功能就补哪个功能的测试；PR 上跑快线（逻辑、迁移、快照），合并到 main 跑慢线（UI 关键流程和无障碍审计），发版前两条都要通过。
- **删测试、改断言的预期值必须写明理由。** 不能为了让 CI 变绿而改测试。
- **有意改了界面要重录快照**，并在 PR 里写清改了哪些页面。
- **部署只走 git → CI。** MCP 只用来查数据、看日志、排查问题；AI 默认只连测试环境。
- **不要引用中央仓库的 `@main`**，用固定的提交加版本注释：`@<SHA> # v1.0.0`。
- **不要在工作流 YAML、日志或提交里写明文密钥**；密钥只在 App 仓库的 Secrets 里。

## 安装本 Skill

它是纯 Markdown，不绑定任何一家 AI。支持 skills 目录的 AI 可以执行：

```bash
npx skills add wenjinliuu/ios-ci-workflows
```

其他 AI 直接读这个目录即可。App 仓库根目录的 `AGENTS.md`（模板在 [templates/AGENTS.md](../../templates/AGENTS.md)）会指向这里。
