#!/usr/bin/env python3
"""按 .ios-ci.yml 的 toolchain.simulator 和 toolchain.ios 精确选模拟器。

快照参考图只在同一机型、同一 iOS 版本上可比，所以找不到就直接失败并列出 runner 上装了什么，
不悄悄换成别的机型。runner 镜像升级后按列表改 .ios-ci.yml，再重录快照。
"""
import json
import os
import subprocess
import sys

name = os.environ["SIMULATOR"]
version = os.environ["IOS_VERSION"]
wanted = "iOS-" + version.replace(".", "-")

devices = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "available", "--json"]))["devices"]
installed = []
for runtime, items in devices.items():
    label = runtime.rsplit(".", 1)[-1]
    if not label.startswith("iOS-"):
        continue
    # 同一小版本的补丁运行时（26.4.1）也算 26.4
    matches_runtime = label == wanted or label.startswith(wanted + "-")
    for device in items:
        if not device["name"].startswith("iPhone"):
            continue
        pretty = label.replace("iOS-", "iOS ").replace("-", ".")
        installed.append(f"{device['name']} ({pretty})")
        if matches_runtime and device["name"] == name:
            with open(os.environ["GITHUB_OUTPUT"], "a") as out:
                out.write(f"udid={device['udid']}\nname={device['name']}\nruntime={pretty}\n")
            print(f"Selected {device['name']} ({pretty}) {device['udid']}")
            sys.exit(0)

print(f"::error::runner 上没有 {name} (iOS {version})。改 .ios-ci.yml 的 toolchain.simulator / toolchain.ios，"
      "然后重录快照。已安装的 iPhone 模拟器：")
for item in sorted(set(installed)):
    print("  " + item)
sys.exit(1)
