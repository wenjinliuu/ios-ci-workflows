import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { GitHubHandler } from "./github-handler";
import type { Props } from "./utils";

type HostedGatewayEnv = Env & {
	CLOUDBASE_API_KEY?: string;
	CLOUDBASE_ENV_ID?: string;
	ALLOWED_GITHUB_LOGIN?: string;
};

type AuthenticatedContext = ExecutionContext & {
	props?: Props;
};

const HOSTED_ORIGIN = "https://tcb-api.cloud.tencent.com";
const HOSTED_MCP_PATH = "/mcp/v1";
const PROTOCOL_VERSION = "2025-06-18";
const TOKEN_EXPIRY_SKEW_MS = 60_000;
const DEFAULT_TOKEN_LIFETIME_SECONDS = 5 * 60;

let cachedHostedToken: { token: string; expiresAt: number } | null = null;
let tokenRefreshInFlight: Promise<string> | null = null;

function base64Url(bytes: Uint8Array): string {
	let binary = "";
	for (const byte of bytes) binary += String.fromCharCode(byte);
	return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function createPkcePair() {
	const verifier = base64Url(crypto.getRandomValues(new Uint8Array(32)));
	const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
	return {
		verifier,
		challenge: base64Url(new Uint8Array(digest)),
	};
}

async function readResponse(response: Response) {
	const text = await response.text();
	let json: Record<string, unknown> | null = null;
	try {
		json = JSON.parse(text) as Record<string, unknown>;
	} catch {
		// Some OAuth errors can be HTML or plain text. Keep only a sanitized snippet.
	}
	return {
		status: response.status,
		text,
		json,
		location: response.headers.get("location"),
	};
}

function sanitizedSnippet(value: string): string {
	return value
		.replace(
			/"(secretId|secretKey|token|sessionToken|apiKey|api_key|access_token|refresh_token)"\s*:\s*"[^"]*"/gi,
			'"$1":"[redacted]"',
		)
		.replace(/Bearer\s+[A-Za-z0-9._~-]+/gi, "Bearer [redacted]")
		.replace(/eyJ[A-Za-z0-9._~-]{20,}/g, "[redacted-token]")
		.slice(0, 2000);
}

function requireString(value: unknown, field: string): string {
	if (typeof value !== "string" || value.length === 0) {
		throw new Error(`Hosted OAuth response is missing ${field}.`);
	}
	return value;
}

async function getHostedAccessToken(env: HostedGatewayEnv): Promise<{
	accessToken: string;
	expiresAt: number;
}> {
	const apiKey = env.CLOUDBASE_API_KEY;
	const envId = env.CLOUDBASE_ENV_ID;
	if (!apiKey || !envId) {
		throw new Error("Missing required CloudBase Worker bindings.");
	}

	const { verifier, challenge } = await createPkcePair();
	const redirectUri = "http://127.0.0.1:8765/callback";

	const register = await readResponse(
		await fetch(`${HOSTED_ORIGIN}/mcp/oauth2/register`, {
			method: "POST",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				client_name: "cloudbase-hosted-oauth-gateway",
				redirect_uris: [redirectUri],
				grant_types: ["authorization_code", "refresh_token"],
				response_types: ["code"],
				token_endpoint_auth_method: "none",
			}),
		}),
	);

	if (register.status !== 201) {
		throw new Error(
			`Hosted OAuth registration failed (${register.status}): ${sanitizedSnippet(register.text)}`,
		);
	}
	const clientId = requireString(register.json?.client_id, "client_id");

	const authorizeUrl = new URL(`${HOSTED_ORIGIN}/mcp/oauth2/authorize`);
	authorizeUrl.search = new URLSearchParams({
		response_type: "code",
		client_id: clientId,
		redirect_uri: redirectUri,
		code_challenge: challenge,
		code_challenge_method: "S256",
		scope: "mcp:full",
		state: "cloudbase-hosted-oauth-gateway",
	}).toString();

	const authorize = await readResponse(
		await fetch(authorizeUrl.toString(), {
			method: "GET",
			redirect: "manual",
		}),
	);
	const authorizeLocation = requireString(authorize.location, "authorize Location header");
	const sessionId = requireString(
		new URL(authorizeLocation).searchParams.get("session_id"),
		"session_id",
	);

	const verify = await readResponse(
		await fetch(`${HOSTED_ORIGIN}/mcp/oauth2/authorize/apikey`, {
			method: "POST",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				session_id: sessionId,
				env_id: envId,
				api_key: apiKey,
			}),
		}),
	);
	if (verify.status !== 200 && verify.status !== 201) {
		throw new Error(
			`Hosted OAuth API-key verification failed (${verify.status}): ${sanitizedSnippet(verify.text)}`,
		);
	}

	const consent = await readResponse(
		await fetch(`${HOSTED_ORIGIN}/mcp/oauth2/authorize/consent`, {
			method: "POST",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				session_id: sessionId,
				env_id: envId,
			}),
			redirect: "manual",
		}),
	);

	let code = typeof consent.json?.code === "string" ? consent.json.code : null;
	if (!code && consent.location) {
		code = new URL(consent.location).searchParams.get("code");
	}
	if (!code) {
		throw new Error(
			`Hosted OAuth consent failed (${consent.status}): ${sanitizedSnippet(consent.text)}`,
		);
	}

	const token = await readResponse(
		await fetch(`${HOSTED_ORIGIN}/mcp/oauth2/token`, {
			method: "POST",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/x-www-form-urlencoded",
			},
			body: new URLSearchParams({
				grant_type: "authorization_code",
				code,
				client_id: clientId,
				redirect_uri: redirectUri,
				code_verifier: verifier,
			}).toString(),
		}),
	);
	if (token.status !== 200) {
		throw new Error(
			`Hosted OAuth token exchange failed (${token.status}): ${sanitizedSnippet(token.text)}`,
		);
	}

	const accessToken = requireString(token.json?.access_token, "access_token");
	const rawExpiresIn = token.json?.expires_in;
	const parsedExpiresIn =
		typeof rawExpiresIn === "number"
			? rawExpiresIn
			: typeof rawExpiresIn === "string"
				? Number(rawExpiresIn)
				: Number.NaN;
	const expiresIn =
		Number.isFinite(parsedExpiresIn) && parsedExpiresIn > 0
			? parsedExpiresIn
			: DEFAULT_TOKEN_LIFETIME_SECONDS;

	return {
		accessToken,
		expiresAt: Date.now() + expiresIn * 1000,
	};
}

async function getCachedHostedToken(env: HostedGatewayEnv, forceRefresh = false): Promise<string> {
	if (
		!forceRefresh &&
		cachedHostedToken &&
		cachedHostedToken.expiresAt > Date.now() + TOKEN_EXPIRY_SKEW_MS
	) {
		return cachedHostedToken.token;
	}

	if (forceRefresh) cachedHostedToken = null;

	if (!tokenRefreshInFlight) {
		tokenRefreshInFlight = getHostedAccessToken(env)
			.then(({ accessToken, expiresAt }) => {
				cachedHostedToken = { token: accessToken, expiresAt };
				return accessToken;
			})
			.finally(() => {
				tokenRefreshInFlight = null;
			});
	}

	return tokenRefreshInFlight;
}

function rewriteInitializeVersion(message: unknown): unknown {
	if (Array.isArray(message)) {
		return message.map(rewriteInitializeVersion);
	}
	if (!message || typeof message !== "object") return message;

	const record = message as Record<string, unknown>;
	if (record.method === "initialize" && record.params && typeof record.params === "object") {
		return {
			...record,
			params: {
				...(record.params as Record<string, unknown>),
				protocolVersion: PROTOCOL_VERSION,
			},
		};
	}
	return record;
}

function jsonRpcGatewayError(id: unknown, message: string): Response {
	return Response.json({
		jsonrpc: "2.0",
		id: id ?? null,
		error: { code: -32000, message },
	});
}

function extractRequestId(message: unknown): unknown {
	if (!message || Array.isArray(message) || typeof message !== "object") {
		return null;
	}
	return (message as Record<string, unknown>).id ?? null;
}

function upstreamHeaders(request: Request, token: string): Headers {
	const headers = new Headers(request.headers);
	headers.set("Authorization", `Bearer ${token}`);
	headers.delete("host");
	headers.delete("content-length");
	headers.delete("cookie");
	for (const name of [
		"cf-connecting-ip",
		"cf-ipcountry",
		"cf-ray",
		"cf-visitor",
		"x-forwarded-for",
		"x-forwarded-host",
		"x-forwarded-proto",
		"x-real-ip",
	]) {
		headers.delete(name);
	}
	if (headers.has("MCP-Protocol-Version")) {
		headers.set("MCP-Protocol-Version", PROTOCOL_VERSION);
	}
	return headers;
}

function downstreamHeaders(upstream: Response): Headers {
	const headers = new Headers(upstream.headers);
	for (const name of [
		"set-cookie",
		"www-authenticate",
		"proxy-authenticate",
		"location",
		"content-length",
		"cf-ray",
		"cf-cache-status",
		"server-timing",
	]) {
		headers.delete(name);
	}
	return headers;
}

async function proxyHostedMcp(request: Request, env: HostedGatewayEnv): Promise<Response> {
	const envId = env.CLOUDBASE_ENV_ID;
	if (!envId) return new Response("Gateway is not configured.", { status: 500 });

	if (!["GET", "POST", "DELETE"].includes(request.method)) {
		return new Response("Method not allowed", {
			status: 405,
			headers: { Allow: "GET, POST, DELETE" },
		});
	}

	let requestBody: Uint8Array | undefined;
	let parsedMessage: unknown = null;
	if (request.method === "POST") {
		requestBody = new Uint8Array(await request.arrayBuffer());
		if (
			(request.headers.get("content-type") ?? "").toLowerCase().includes("application/json")
		) {
			try {
				parsedMessage = JSON.parse(new TextDecoder().decode(requestBody));
				requestBody = new TextEncoder().encode(
					JSON.stringify(rewriteInitializeVersion(parsedMessage)),
				);
			} catch {
				return jsonRpcGatewayError(null, "Invalid JSON-RPC payload.");
			}
		}
	}

	const upstreamUrl = new URL(HOSTED_MCP_PATH, HOSTED_ORIGIN);
	upstreamUrl.searchParams.set("env_id", envId);

	const send = async (forceRefresh: boolean) => {
		const token = await getCachedHostedToken(env, forceRefresh);
		return fetch(upstreamUrl.toString(), {
			method: request.method,
			headers: upstreamHeaders(request, token),
			body: request.method === "POST" ? requestBody : undefined,
			redirect: "manual",
		});
	};

	try {
		let upstream = await send(false);
		if (upstream.status === 401) {
			await upstream.body?.cancel();
			upstream = await send(true);
		}

		if (upstream.status === 401 || upstream.status === 403) {
			await upstream.body?.cancel();
			return jsonRpcGatewayError(
				extractRequestId(parsedMessage),
				"CloudBase Hosted MCP authentication failed upstream.",
			);
		}

		return new Response(upstream.body, {
			status: upstream.status,
			headers: downstreamHeaders(upstream),
		});
	} catch (error) {
		console.error(
			"Hosted MCP gateway error:",
			error instanceof Error ? sanitizedSnippet(error.message) : "Unknown gateway error",
		);
		return jsonRpcGatewayError(
			extractRequestId(parsedMessage),
			"CloudBase Hosted MCP gateway request failed.",
		);
	}
}

const hostedGateway = {
	async fetch(request, env, ctx) {
		const props = (ctx as AuthenticatedContext).props;
		const allowedLogin = env.ALLOWED_GITHUB_LOGIN;
		if (!allowedLogin || props?.login !== allowedLogin) {
			return new Response("Forbidden", { status: 403 });
		}
		return proxyHostedMcp(request, env);
	},
} satisfies ExportedHandler<HostedGatewayEnv>;

export default new OAuthProvider({
	apiHandler: hostedGateway,
	apiRoute: "/mcp",
	authorizeEndpoint: "/authorize",
	clientRegistrationEndpoint: "/register",
	defaultHandler: GitHubHandler as any,
	tokenEndpoint: "/token",
});
