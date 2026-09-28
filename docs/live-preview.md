# Live Preview：手机浏览器里的模拟器

手动运行 App 仓库的 **Live Preview**，几分钟后 job 日志和 summary 里会出现一个地址，用手机打开、输入预览密码，就能看画面、点击、滑动、输入文字。它是给人调 UI、复现 bug、演示用的，不是测试；AI 验证改动靠 Build & Test 的测试报告。

```text
serve-sim（画面 + 触控，只监听 127.0.0.1:3200）
  → preview-proxy.cjs 密码网关（127.0.0.1:3210，只转发画面和 HID 触控，屏蔽 shell 接口）
  → cloudflared 隧道
  → 手机浏览器
```

开放给你之前，工作流会通过公网地址自动验证：密码登录、JPEG 画面帧、HID WebSocket，以及带 shell 能力的 `/exec-ws` 返回 404。

## 默认：Quick Tunnel（零配置）

不需要 Cloudflare 账号、域名或 token。工作流下载固定版本的 `cloudflared`（校验 SHA-256），申请一个临时的 `*.trycloudflare.com` 地址；DNS 迟迟不解析时重新申请，最多 4 次。地址每次都不同，只在 job 运行期间有效。

地址公开但随机，靠 ≥12 位密码、临时地址、到时自动关闭来保护。

## 可选：固定域名 Named Tunnel

Quick Tunnel 在你的网络下经常解析不了，或者想要固定地址、想用 Cloudflare Access 只认身份时才需要。需要一个托管在 Cloudflare 的域名，**每个 App 一条独立的 Tunnel 和主机名**，避免同时预览时串到别的模拟器。

1. Cloudflare Dashboard → **Networking → Tunnels** → 创建远程管理（remotely managed）的 Tunnel。
2. 添加 **Published application** 路由，如 `myapp-preview.example.com` → Service `http://127.0.0.1:3210`，**不要**加路径限制（登录、MJPEG、WebSocket 都要能到达网关）。
3. App 仓库添加 Variable `AGENT_PREVIEW_URL`（`https://myapp-preview.example.com`）和 Secret `AGENT_PREVIEW_TUNNEL_TOKEN`（这条 Tunnel 的 token）。token 不要写进工作流 YAML 或日志。
4. （可选）在这个主机名上再套一层 Cloudflare Access。

两项必须同时设置，否则工作流直接报错；都不设置时回到 Quick Tunnel。token 以 `600` 权限写入临时文件，随 runner 销毁。

## 局限

- 编码只能用 MJPEG（H.264 在 GitHub runner 上不出画面）；嫌卡时降分辨率和帧率比换编码有效。
- 有延迟、不是真机手感、消耗 macOS 分钟数；串流里看到的卡顿可能来自传输，不一定是 App 本身。
- 你和 AI 共用同一台模拟器，没有控制权锁：AI 在操作时只看不点。

## AI 实时操作（暂缓）

AI 通过 MCP 截图、点击、滑动，你同时看串流。AI 是“截图 → 思考 → 点击”逐步进行，看不到动画掉帧；探路所需的“界面地图”已由每次 Build & Test 的 `ui-tree.json` 提供，目前没有建。以后需要时，用 agent-device 以代理模式挂在同一条隧道上，并参照 [native-sim](https://github.com/bidah/native-sim) 关掉服务空闲、测试进程空闲、设备租约三个默认 5 分钟的超时，加守护进程自动重启。
