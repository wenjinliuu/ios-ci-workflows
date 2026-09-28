#!/usr/bin/env python3
"""决定这次 Build & Test 跑哪些测试（快线 / 慢线 / 全部），输出给测试 job 用。

范围（suite）：
- fast：快线，build_test.fast_test_plan（逻辑 + 迁移 + 快照，不含 UI 测试）
- ui：慢线，只跑 build_test.ui_test_target（UI 关键流程 + 无障碍审计）
- full：全部，build_test.full_test_plan
- default：没配两份计划时的老行为，跑 build_test.test_plan 或 scheme 的全部测试

没指定 suite 时：配了两份计划就按触发方式选，推送到默认分支跑 ui，其余（PR、分支推送、手动）跑 fast；
没配就是 default，已有的调用方行为不变。
"""
import json
import os
import sys


def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)


def resolve(build_test: dict, requested: str, event: str, ref: str, default_branch: str) -> dict:
    fast = build_test.get("fast_test_plan") or ""
    full = build_test.get("full_test_plan") or ""
    ui_target = build_test.get("ui_test_target") or ""
    legacy_plan = build_test.get("test_plan") or ""

    requested = requested.strip()
    if requested not in ("", "fast", "full", "ui"):
        fail(f"suite 只能是 fast、full 或 ui，收到的是 {requested}")
    if requested:
        suite = requested
    elif fast and full:
        suite = "ui" if event == "push" and ref == f"refs/heads/{default_branch}" else "fast"
    else:
        suite = "default"

    only_testing = ""
    if suite == "fast":
        if not fast:
            fail(".ios-ci.yml 的 build_test.fast_test_plan 没写，跑不了快线")
        plan = fast
    elif suite == "ui":
        if not ui_target:
            fail(".ios-ci.yml 的 build_test.ui_test_target 没写，跑不了慢线")
        plan = full or legacy_plan
        only_testing = ui_target
    elif suite == "full":
        plan = full or legacy_plan
    else:
        plan = legacy_plan
    return {"suite": suite, "plan": plan, "only_testing": only_testing}


def main() -> None:
    config = json.loads(os.environ["CONFIG"])
    result = resolve(config["build_test"], os.environ.get("REQUESTED", ""), os.environ.get("EVENT", ""),
                     os.environ.get("REF", ""), os.environ.get("DEFAULT_BRANCH", ""))
    print(f"suite={result['suite']} plan={result['plan'] or '(scheme)'} only_testing={result['only_testing'] or '-'}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            for key, value in result.items():
                out.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
