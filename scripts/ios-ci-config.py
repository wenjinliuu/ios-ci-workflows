#!/usr/bin/env python3
"""读取 App 仓库的 .ios-ci.yml，补上默认值并校验，输出一个 JSON 给后面的 job 用。

所有可复用工作流的第一个 job 都跑这个脚本，结果写进 GITHUB_OUTPUT 的 config，
后面的 job 用 fromJSON(needs.config.outputs.config).<键> 取值。
"""
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # runner 镜像不一定带 PyYAML
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--user",
                           "--break-system-packages", "pyyaml==6.0.3"])
    import site

    sys.path.append(site.getusersitepackages())
    import yaml

DEFAULTS = {
    "workdir": ".",
    "project": None,
    "scheme": None,
    "bundle_id": None,
    "display_name": "",
    "sync_command": "true",
    "generate_command": "true",
    "icon_path": "",
    "toolchain": {
        "xcode": "26.6",
        "simulator": "iPhone 17 Pro",
        "ios": "26.4",
    },
    "build_test": {
        "test_plan": "",
        "accessibility_audit": "warn",
        "accessibility_test_pattern": "(?i)accessibility",
        "commit_recorded_snapshots": False,
    },
    "app_icon": {
        "commit_previews": False,
        "previews_dir": "DesignAssets/AppIcon/previews",
    },
    "testflight": {
        "entitlements_path": "",
        "entitlement_mode": "none",
        "icloud_container": "",
        "expected_team_id": "",
        "artifact_prefix": "",
        "inspect_icloud": False,
        "acceptance_issue": False,
        "acceptance_checklist": ".github/release-checklist.md",
        "acceptance_extra": ".github/release-checklist-current.md",
    },
}

REQUIRED = ("project", "scheme", "bundle_id")


def merge(defaults: dict, values: dict, where: str) -> dict:
    unknown = set(values) - set(defaults)
    if unknown:
        fail(f"{where or '顶层'}里有不认识的键：{', '.join(sorted(unknown))}")
    merged = {}
    for key, default in defaults.items():
        value = values.get(key, default)
        if isinstance(default, dict):
            if not isinstance(value, dict):
                fail(f"{where}{key} 应该是一组键值")
            value = merge(default, value, f"{where}{key}.")
        elif value is None and key in values:
            value = default
        merged[key] = value
    return merged


def fail(message: str) -> None:
    print(f"::error::.ios-ci.yml：{message}")
    sys.exit(1)


def main() -> None:
    path = Path(os.environ.get("CONFIG_PATH") or ".ios-ci.yml")
    if not path.is_file():
        fail(f"App 仓库里没有 {path}；从 ios-ci-workflows 的 templates/ 复制一份再改")
    raw = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw, dict):
        fail("顶层应该是键值")
    config = merge(DEFAULTS, raw, "")

    # 工作流可以用 REQUIRE 追加必填键，比如 App Icon 要 icon_path
    extra = [key for key in os.environ.get("REQUIRE", "").split(",") if key]
    for key in (*REQUIRED, *extra):
        if not config[key]:
            fail(f"缺少 {key}")
    for key in ("xcode", "ios"):
        if not isinstance(config["toolchain"][key], str):
            fail(f"toolchain.{key} 要加引号（如 '26.4'），不加引号 26.10 会被读成 26.1")
        if not re.fullmatch(r"\d+(\.\d+){1,2}", config["toolchain"][key]):
            fail(f"toolchain.{key} 要写完整版本号（如 26.4），不能只写大版本")
    if config["build_test"]["accessibility_audit"] not in ("warn", "fail"):
        fail("build_test.accessibility_audit 只能是 warn 或 fail")
    mode = config["testflight"]["entitlement_mode"]
    if mode not in ("none", "required", "best-effort", "icloud-verified"):
        fail("testflight.entitlement_mode 只能是 none、required、best-effort、icloud-verified")
    if mode != "none" and not config["testflight"]["entitlements_path"]:
        fail("testflight.entitlement_mode 不是 none 时要写 entitlements_path")
    if mode == "icloud-verified" and not config["testflight"]["icloud_container"]:
        fail("testflight.entitlement_mode 为 icloud-verified 时要写 icloud_container")

    encoded = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps(config, ensure_ascii=False, indent=2))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"config={encoded}\n")


if __name__ == "__main__":
    main()
