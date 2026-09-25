# ios-ci-workflows
# Shared iOS CI

Reusable workflows for `lottery-ios`, `calenease` and `cichu-ios`:

- `app-icon.yml`: unsigned Xcode archive verifies the native `.icon` bundle; an optional third-party renderer uploads previews.
- `agent-preview.yml`: unsigned Simulator XCTest, app launch, screenshot, XcodeBuildMCP accessibility snapshot, logs and optional authenticated browser session.
- `testflight-release.yml`: shared unsigned archive, optional Apple registration check, entitlement embedding, export signing and upload; supports a dry-run archive with no upload.

Each App calls a fixed commit SHA and keeps its own parameters and secrets. The run and artifacts stay in the calling App repository. `scripts/preview-proxy.cjs` is fetched at the same pinned commit only for a manually requested live session.

### Live browser preview

Set an App repository secret named `AGENT_PREVIEW_PASSWORD` (at least 12 characters); manually dispatch its Build & Test workflow with `live_preview=true`. The active Actions job log displays an expiring Quick Tunnel address as a notice. Open it while the job is running; the address is also recorded in the job summary. Enter the repository password on the login page. The dedicated viewer offers a live stream, taps, swipes, text entry, UI Tree and recent app logs. Its gateway only forwards the simulator video and HID socket; it never forwards serve-sim's shell-capable `/exec-ws` or developer tools. The job exits after at most 20 minutes. Do not use production accounts or sensitive real user data in a preview build.

Automatic push/PR runs only produce test results, a launch screenshot, an accessibility snapshot if supported by that runtime, and simulator logs. Live sessions do not persist after a runner job exits. To change Simulator targets, set `simulator_name` and `ios_runtime` at manual dispatch. The default is iPhone 17 Pro / iOS 26 (with a model fallback within iOS 26 if necessary).

TestFlight uploads remain manually dispatched or `v*` tag triggered; inspect their output before changing signing/provisioning steps.
