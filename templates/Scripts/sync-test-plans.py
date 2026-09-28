#!/usr/bin/env python3
"""把 .xcodeproj 里的 target ID 填进同目录的 *.xctestplan。

测试计划按 ID 引用 target。用 XcodeGen 时 .xcodeproj 每次重新生成、不进仓库，
所以把这个脚本接在生成命令后面（在 .xcodeproj 所在目录运行）：

    generate_command: xcodegen generate && python3 Scripts/sync-test-plans.py

它按 target 名字找到 ID 写回每份计划；ID 没变就不改文件。已提交 .xcodeproj 的项目不需要它。
"""
import json
import re
import sys
from pathlib import Path

HERE = Path.cwd()


def main() -> None:
    projects = sorted(HERE.glob("*.xcodeproj"))
    if len(projects) != 1:
        sys.exit(f"在 {HERE} 里要正好一个 .xcodeproj，找到 {len(projects)} 个")
    project = projects[0]
    text = (project / "project.pbxproj").read_text()
    ids = {name: ident for ident, name in
           re.findall(r"([0-9A-F]{24}) /\* ([^*]+?) \*/ = \{\s*isa = PBXNativeTarget;", text)}
    container = f"container:{project.name}"

    def fill(node, plan: Path) -> None:
        if isinstance(node, dict):
            if node.get("containerPath") == container and "name" in node:
                if node["name"] not in ids:
                    sys.exit(f"{plan.name}：{project.name} 里没有 target {node['name']}")
                node["identifier"] = ids[node["name"]]
            for value in node.values():
                fill(value, plan)
        elif isinstance(node, list):
            for value in node:
                fill(value, plan)

    for plan in sorted(HERE.glob("*.xctestplan")):
        data = json.loads(plan.read_text())
        fill(data, plan)
        updated = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if updated != plan.read_text():
            plan.write_text(updated)
            print(f"更新了 {plan.name} 里的 target ID")


if __name__ == "__main__":
    main()
