# ios-ci-workflows
# Shared iOS CI

Reusable workflows for `lottery-ios`, `calenease` and `cichu-ios`:

- `app-icon.yml`: unsigned Xcode archive verifies the native `.icon` bundle; an optional third-party renderer uploads previews.
- `agent-preview.yml`: unsigned Simulator XCTest, app launch, screenshot, XcodeBuildMCP accessibility snapshot, logs and optional authenticated browser session.

Each App calls a fixed commit SHA and keeps its own parameters and secrets. The run and artifacts stay in the calling App repository. `scripts/preview-proxy.cjs` is fetched at the same pinned commit only for a manually requested live session.

### Live browser preview

Set an App repository secret named `AGENT_PREVIEW_PASSWORD` (at least 12 characters); manually dispatch its Build & Test workflow with `live_preview=true`. The Actions job summary shows an expiring Quick Tunnel address. Enter the repository password on the login page. The viewer supports video and browser interactions; host command endpoints are filtered at the proxy. The job exits after at most 20 minutes. Do not use production accounts or sensitive real user data in a preview build.

Automatic push/PR runs only produce test results, a launch screenshot, an accessibility snapshot if supported by that runtime, and simulator logs. Live sessions do not persist after a runner job exits. To change Simulator targets, set `simulator_name` and `ios_runtime` at manual dispatch. The default is iPhone 17 Pro / iOS 26 (with a model fallback within iOS 26 if necessary).

TestFlight uploads remain manually dispatched or `v*` tag triggered; inspect their output before changing signing/provisioning steps.
