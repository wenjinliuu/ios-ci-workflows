#!/usr/bin/env python3
"""核对 App Store Connect 上实际注册的 App 与 Bundle ID。

用仓库已有的 App Store Connect API 密钥（环境变量 KEY_ID / ISSUER_ID，
私钥在 ~/.appstoreconnect/private_keys/AuthKey_<KEY_ID>.p8）只读查询：

- 列出团队下全部 iOS Bundle ID 与 App（名称、Bundle ID、SKU、主要语言）
- 设置了 EXPECTED_BUNDLE_ID 时，确认它已注册、已有对应 App，并打印它的能力（iCloud 等）；
  任何一项缺失都以非零退出，让 TestFlight 在归档之前就失败，而不是等到导出签名。
- 再设置 ICLOUD_CONTAINER 时，从这个 Bundle ID 现有的描述文件里读出 App ID 实际勾选的
  iCloud 容器，把 `icloud=true|false` 写进 GITHUB_OUTPUT：容器确实在才给包加 iCloud 权限，
  不在（Bundle ID 没开 iCloud、没勾这个容器，或还没有描述文件可查）就跳过并给出警告，
  App 里的备份自动落到本机。

依赖：pip install 'pyjwt[crypto]'
"""

import base64
import json
import os
import plistlib
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import jwt

API = "https://api.appstoreconnect.apple.com"


def token() -> str:
    key_id = os.environ["KEY_ID"]
    issuer = os.environ["ISSUER_ID"]
    key_path = Path.home() / ".appstoreconnect/private_keys" / f"AuthKey_{key_id}.p8"
    now = int(time.time())
    return jwt.encode(
        {"iss": issuer, "iat": now, "exp": now + 15 * 60, "aud": "appstoreconnect-v1"},
        key_path.read_text(),
        algorithm="ES256",
        headers={"kid": key_id, "typ": "JWT"},
    )


def get(path: str, params: dict | None = None, auth: str = "") -> list[dict]:
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    items: list[dict] = []
    while url:
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {auth}"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.load(response)
        data = body.get("data", [])
        items.extend(data if isinstance(data, list) else [data])
        url = body.get("links", {}).get("next")
    return items


def icloud_containers(bundle_pk: str, auth: str) -> set[str]:
    """从这个 Bundle ID 现有的描述文件里读出 App ID 实际勾选的 iCloud 容器。

    API 不直接列容器，但描述文件的 Entitlements 里写着 App ID 允许的全部容器。
    """
    containers: set[str] = set()
    profiles = get(f"/v1/bundleIds/{bundle_pk}/profiles",
                   {"fields[profiles]": "name,profileType,profileState,profileContent"}, auth)
    for profile in profiles:
        a = profile["attributes"]
        raw = base64.b64decode(a.get("profileContent") or "")
        match = re.search(rb"<\?xml.*?</plist>", raw, re.S)
        if not match:
            continue
        entitlements = plistlib.loads(match.group(0)).get("Entitlements", {})
        found = entitlements.get("com.apple.developer.icloud-container-identifiers", [])
        print(f"    描述文件 {a['name']!r}（{a['profileType']}，{a['profileState']}）iCloud 容器：{found or '（无）'}")
        containers.update(found)
    return containers


def main() -> int:
    auth = token()
    expected = os.environ.get("EXPECTED_BUNDLE_ID", "").strip()

    bundle_ids = get("/v1/bundleIds", {"limit": 200, "fields[bundleIds]": "identifier,name,platform,seedId"}, auth)
    apps = get("/v1/apps", {"limit": 200, "fields[apps]": "name,bundleId,sku,primaryLocale"}, auth)

    print("=== Bundle IDs（Apple Developer › Identifiers）===")
    for item in sorted(bundle_ids, key=lambda b: b["attributes"]["identifier"]):
        a = item["attributes"]
        caps = get(f"/v1/bundleIds/{item['id']}/bundleIdCapabilities", auth=auth)
        names = ",".join(sorted(c["attributes"]["capabilityType"] for c in caps)) or "-"
        print(f"  {a['identifier']:<45} name={a['name']!r} platform={a['platform']} capabilities={names}")
        if "ICLOUD" in names:
            icloud_containers(item["id"], auth)

    print("=== Apps（App Store Connect）===")
    for item in apps:
        a = item["attributes"]
        print(f"  {a['name']!r:<24} bundleId={a['bundleId']} sku={a['sku']} locale={a['primaryLocale']} appleId={item['id']}")

    if not expected:
        return 0

    print(f"=== 核对 {expected} ===")
    ok = True
    bundle = next((b for b in bundle_ids if b["attributes"]["identifier"] == expected), None)
    if bundle is None:
        print(f"::error::Apple Developer 里没有注册 Bundle ID {expected}")
        ok = False
    else:
        caps = get(f"/v1/bundleIds/{bundle['id']}/bundleIdCapabilities", auth=auth)
        names = sorted(c["attributes"]["capabilityType"] for c in caps)
        print(f"  Bundle ID 已注册：name={bundle['attributes']['name']!r}，能力：{', '.join(names) or '（无）'}")
        required = [c for c in os.environ.get("REQUIRED_CAPABILITIES", "").split(",") if c]
        for capability in required:
            if capability not in names:
                print(f"::error::Bundle ID {expected} 没有打开 {capability} 能力")
                ok = False

    container = os.environ.get("ICLOUD_CONTAINER", "").strip()
    if container and bundle is not None:
        found = icloud_containers(bundle["id"], auth) if "ICLOUD" in names else set()
        enabled = container in found
        if enabled:
            print(f"  iCloud 容器 {container} 已勾选在 App ID 上")
        elif "ICLOUD" not in names:
            print(f"::warning::Bundle ID {expected} 没有开启 iCloud 能力；这次不加 iCloud 权限")
        elif found:
            print(f"::warning::App ID {expected} 勾选的 iCloud 容器是 {sorted(found)}，不含 {container}；这次不加 iCloud 权限")
        else:
            print(f"::warning::还没有 {expected} 的描述文件可以核对 iCloud 容器（首次导出后才会生成）；这次不加 iCloud 权限")
        output = os.environ.get("GITHUB_OUTPUT")
        if output:
            with open(output, "a") as handle:
                handle.write(f"icloud={'true' if enabled else 'false'}\n")

    app = next((a for a in apps if a["attributes"]["bundleId"] == expected), None)
    if app is None:
        print(f"::error::App Store Connect 里没有 Bundle ID 为 {expected} 的 App")
        ok = False
    else:
        a = app["attributes"]
        print(f"  App 已创建：name={a['name']!r} sku={a['sku']} appleId={app['id']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
