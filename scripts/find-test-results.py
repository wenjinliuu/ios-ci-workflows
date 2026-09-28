#!/usr/bin/env python3
"""TestFlight 的测试门槛：查这个提交已经跑过的 Build & Test，够了就不再重跑。

够的条件（任一）：
- 这个提交有一次成功的 full（或没配快线慢线时的 default）运行；
- 这个提交有一次成功的 ui 运行，并且有一次成功的 fast 运行：可以是这个提交本身，
  也可以是合并出这个提交的 PR 的最后一个提交（PR 上跑的是 fast，合并到 main 后跑的是 ui）。

靠 Build & Test 测试 job 的名字识别范围：它叫 “test (fast)”、“test (ui)” 这样。
查询要 actions: read（和私有仓库的 pull-requests: read）；查不到、没权限或结果不够，都回到现场跑 full。
只用标准库。
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ.get("GH_TOKEN", "")
JOB_NAME = re.compile(r"(?:^|/ )test \((fast|ui|full|default)\)$")


def get(path: str):
    request = urllib.request.Request(f"{API}{path}", headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def passed_suites(sha: str) -> dict[str, str]:
    """这个提交上成功过的范围 → 运行链接。"""
    found: dict[str, str] = {}
    runs = get(f"/repos/{REPO}/actions/runs?head_sha={sha}&status=success&per_page=100")["workflow_runs"]
    for run in runs:
        jobs = get(f"/repos/{REPO}/actions/runs/{run['id']}/jobs?per_page=100")["jobs"]
        for job in jobs:
            match = JOB_NAME.search(job["name"])
            if match and job.get("conclusion") == "success":
                found.setdefault(match.group(1), run["html_url"])
    return found


def pull_request_heads(sha: str) -> list[str]:
    pulls = get(f"/repos/{REPO}/commits/{sha}/pulls")
    return [pull["head"]["sha"] for pull in pulls if pull.get("merged_at") and pull["head"]["sha"] != sha]


def decide(sha: str) -> tuple[bool, list[str]]:
    notes = []
    here = passed_suites(sha)
    for suite in ("full", "default"):
        if suite in here:
            return True, [f"{sha[:7]} 已通过全部测试：{here[suite]}"]
    if "ui" not in here:
        return False, [f"{sha[:7]} 没有成功的 ui 运行"]
    notes.append(f"ui：{here['ui']}")
    if "fast" in here:
        return True, notes + [f"fast：{here['fast']}"]
    for head in pull_request_heads(sha):
        there = passed_suites(head)
        for suite in ("fast", "full", "default"):
            if suite in there:
                return True, notes + [f"{suite}（PR 的最后一个提交 {head[:7]}）：{there[suite]}"]
    return False, notes + [f"{sha[:7]} 和合并它的 PR 上都没有成功的 fast 运行"]


def main() -> int:
    sha = os.environ["SHA"]
    try:
        reuse, notes = decide(sha)
    except (urllib.error.URLError, KeyError, ValueError) as error:
        reuse, notes = False, [f"查询已有结果失败（{error}）；入口文件要给 actions: read 和 pull-requests: read"]
    verdict = "复用已有结果，跳过重复测试" if reuse else "现场跑一次全部测试"
    lines = [f"### 测试门槛：{verdict}", ""] + [f"- {note}" for note in notes]
    print("\n".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as out:
            out.write("\n".join(lines) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as out:
            out.write(f"reuse={'true' if reuse else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
