#!/usr/bin/env python3
"""把一次 xcodebuild test 的结果整理成一份给人和 AI 读的报告。

读 Test.xcresult（xcresulttool），输出：
- report.md：测试总数、失败的测试及原因、快照对比图、无障碍问题、新录制的快照；
  同时追加到 job summary
- report.json：同样的内容，给 AI 或脚本读
- attachments/：失败测试带的附件（快照的 reference / failure / difference 图等）

失败分三类，通过/失败规则由 CI 的最后一步按这里的分类决定：
- accessibility：测试名匹配 ACCESSIBILITY_PATTERN 的失败（无障碍审计），ACCESSIBILITY_MODE=warn 时只警告
- snapshot：快照与参考图不一致、或刚录制了新参考图
- test：其余所有失败（逻辑测试、关键流程）

依赖：只用标准库；在 macOS runner 上调用 xcrun xcresulttool（Xcode 16+ 的新接口）。
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SNAPSHOT_HINTS = ("snapshot", "automatically recorded", "no reference was found")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".heic")


def xcresulttool(*args: str) -> str:
    return subprocess.check_output(["xcrun", "xcresulttool", *args], text=True)


def load_summary(bundle: Path) -> dict:
    return json.loads(xcresulttool("get", "test-results", "summary", "--path", str(bundle), "--format", "json"))


def export_failure_attachments(bundle: Path, out: Path) -> list[dict]:
    """导出失败测试的附件，返回 manifest（每个测试一项，含 attachments 列表）。"""
    out.mkdir(parents=True, exist_ok=True)
    try:
        xcresulttool("export", "attachments", "--path", str(bundle), "--output-path", str(out), "--only-failures")
    except subprocess.CalledProcessError as error:
        print(f"::warning::导出失败附件出错：{error}")
        return []
    manifest = out / "manifest.json"
    return json.loads(manifest.read_text()) if manifest.exists() else []


def test_name(failure: dict) -> str:
    return failure.get("testIdentifierString") or "/".join(
        part for part in (failure.get("targetName"), failure.get("testName")) if part)


def classify(failure: dict, pattern: re.Pattern) -> str:
    if pattern.search(test_name(failure)):
        return "accessibility"
    text = (failure.get("failureText") or "").lower()
    if any(hint in text for hint in SNAPSHOT_HINTS):
        return "snapshot"
    return "test"


def attachments_by_test(manifest: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for entry in manifest:
        key = entry.get("testIdentifier") or entry.get("testIdentifierString") or ""
        grouped.setdefault(key, []).extend(entry.get("attachments", []))
    return grouped


def build_report(summary: dict | None, manifest: list[dict], *, built: bool, pattern: str, device: str,
                 test_plan: str, recorded: list[str], build_log_errors: list[str]) -> dict:
    regex = re.compile(pattern)
    attachments = attachments_by_test(manifest)
    failures = []
    for failure in (summary or {}).get("testFailures", []):
        name = test_name(failure)
        failures.append({
            "test": name,
            "kind": classify(failure, regex),
            "reason": (failure.get("failureText") or "").strip(),
            "attachments": [a.get("exportedFileName") for a in attachments.get(name, [])
                            if a.get("exportedFileName")],
        })
    counts = {key: (summary or {}).get(key, 0)
              for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests", "expectedFailures")}
    configurations = sorted({
        " · ".join(filter(None, (item.get("configuration", {}).get("configurationName"),
                                 item.get("device", {}).get("deviceName"),
                                 item.get("device", {}).get("osVersion"))))
        for item in (summary or {}).get("devicesAndConfigurations", [])
    } - {""})
    return {
        "built": built,
        "result": (summary or {}).get("result", "No results"),
        "device": device,
        "test_plan": test_plan,
        "configurations": configurations,
        "counts": counts,
        "failures": failures,
        "recorded_snapshots": recorded,
        "build_errors": build_log_errors,
    }


def one_line(text: str, limit: int = 300) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def render_markdown(report: dict, *, accessibility_mode: str, record_mode: bool) -> str:
    lines = ["## 测试报告", ""]
    if not report["built"]:
        lines += ["**编译失败，没有测试结果。** 下面是 xcodebuild.log 里的错误（完整日志在产物里）：", ""]
        lines += [f"    {line}" for line in report["build_errors"][:40]] or ["    （日志里没有找到 error: 行）"]
        return "\n".join(lines) + "\n"

    c = report["counts"]
    lines.append(f"结果：**{report['result']}** · 共 {c['totalTestCount']} 个测试，通过 {c['passedTests']}，"
                 f"失败 {c['failedTests']}，跳过 {c['skippedTests']}")
    lines.append(f"模拟器：{report['device']}" + (f" · 测试计划：{report['test_plan']}" if report["test_plan"] else ""))
    if report["configurations"]:
        lines.append("配置：" + "；".join(report["configurations"]))
    lines.append("")

    groups = {
        "test": "失败的测试",
        "snapshot": "快照不一致" + ("（录制模式，已重新录制）" if record_mode else ""),
        "accessibility": "无障碍问题" + ("（只警告，不阻断）" if accessibility_mode == "warn" else ""),
    }
    for kind, title in groups.items():
        items = [f for f in report["failures"] if f["kind"] == kind]
        if not items:
            continue
        lines += [f"### {title}（{len(items)}）", "", "| 测试 | 原因 | 附件 |", "| --- | --- | --- |"]
        for item in items:
            files = "<br>".join(f"`{name}`" for name in item["attachments"]) or "—"
            lines.append(f"| `{item['test']}` | {one_line(item['reason'])} | {files} |")
        lines.append("")
    if any(f["attachments"] for f in report["failures"]):
        lines += ["附件（快照的 reference / failure / difference 图等）在产物 `agent-preview-<run>` 的 `report/attachments/` 里。", ""]

    if report["recorded_snapshots"]:
        lines += [f"### 新录制的快照参考图（{len(report['recorded_snapshots'])}）", "",
                  "已打包为产物 `recorded-snapshots-<run>`，按原路径解压后提交回 App 仓库：", ""]
        lines += [f"- `{path}`" for path in report["recorded_snapshots"]]
        lines.append("")
    if not report["failures"]:
        lines.append("全部通过。")
    return "\n".join(lines) + "\n"


def main() -> int:
    bundle = Path(os.environ["XCRESULT"])
    out = Path(os.environ["REPORT_DIR"])
    out.mkdir(parents=True, exist_ok=True)
    recorded_list = Path(os.environ.get("RECORDED_LIST", ""))
    recorded = recorded_list.read_text().split("\n") if recorded_list.is_file() else []
    log = Path(os.environ.get("BUILD_LOG", ""))
    # 编译错误行；测试失败也会写成 "error: -[Suite test] : failed"，不算在内
    errors = [line.strip() for line in log.read_text(errors="replace").splitlines()
              if (" error: " in line or line.startswith("error:")) and "] : failed" not in line] if log.is_file() else []

    built = os.environ.get("BUILT") == "true"
    summary = None
    if bundle.exists():
        try:
            summary = load_summary(bundle)
        except (subprocess.CalledProcessError, ValueError) as error:
            print(f"::warning::读取 {bundle} 失败：{error}")
    manifest = export_failure_attachments(bundle, out / "attachments") if summary else []
    if summary:
        (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    report = build_report(summary, manifest, built=built,
                          pattern=os.environ.get("ACCESSIBILITY_PATTERN", "(?i)accessibility"),
                          device=os.environ.get("DEVICE", ""), test_plan=os.environ.get("TEST_PLAN", ""),
                          recorded=[p for p in recorded if p], build_log_errors=errors)
    markdown = render_markdown(report, accessibility_mode=os.environ.get("ACCESSIBILITY_MODE", "warn"),
                               record_mode=os.environ.get("RECORD_SNAPSHOTS") == "true")
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (out / "report.md").write_text(markdown)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as handle:
            handle.write(markdown)
    kinds = [f["kind"] for f in report["failures"]]
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
            handle.write(f"built={'true' if report['built'] else 'false'}\n")
            for kind in ("test", "snapshot", "accessibility"):
                handle.write(f"{kind}_failures={kinds.count(kind)}\n")
    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
