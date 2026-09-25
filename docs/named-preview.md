# Stable browser preview with a named Cloudflare Tunnel

The default preview creates a temporary `trycloudflare.com` hostname. If Quick Tunnel DNS does not resolve reliably, use a named tunnel with a hostname in a domain managed by Cloudflare. The login password gateway and blocked shell endpoints remain in place.

Set up **a separate tunnel and hostname for each App** so simultaneous previews cannot route to the wrong Simulator:

1. In Cloudflare **Networking → Tunnels**, create a remotely managed tunnel for the App.
2. Add a **Published application** route such as `calenease-preview.example.com`, with Service URL `http://127.0.0.1:3210`. The route must have no path restriction so login, MJPEG and WebSocket requests all reach the gateway.
3. In that App's GitHub repository, add an Actions variable `AGENT_PREVIEW_URL` with `https://calenease-preview.example.com` and an Actions secret `AGENT_PREVIEW_TUNNEL_TOKEN` with that tunnel's token. Keep `AGENT_PREVIEW_PASSWORD` as a separate secret. Never paste a tunnel token in workflow YAML or logs.
4. Run **Build & Test / Agent Preview** manually and enable **Open authenticated browser preview**. The run summary links to the fixed hostname while the job is alive. The runner verifies login, a JPEG frame, the HID WebSocket, and that the shell endpoint is inaccessible before the preview opens.

Use one unique token, hostname and password per App. The hostname remains registered after the Actions job ends, but the preview gateway and Simulator stop with the job. Protect access with the gateway password and optionally Cloudflare Access. The workflow writes the tunnel token to a temporary file with mode `600` and removes it with the ephemeral runner; Quick Tunnel remains the default until both variable and secret are configured.
