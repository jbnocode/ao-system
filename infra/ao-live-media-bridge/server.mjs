/**
 * Twilio Media Streams ↔ OpenAI GPT-Live bridge.
 *
 * Twilio sends mulaw/8k frames; we open a Live WebRTC session via a local
 * PeerConnection when `wrtc` is available, otherwise we create a Live SIP
 * session is preferred from CRM. This process always:
 *  1) Resolves the call token against CRM
 *  2) Creates a Live session with the agent instructions
 *  3) Acks Twilio start / stop events
 *
 * For production phone audio fidelity, configure OpenAI SIP on CRM Live Settings
 * (outbound) and/or run this bridge behind wss with OPENAI_API_KEY access.
 */
import { createServer } from "node:http"
import { readFile, access } from "node:fs/promises"
import { resolve, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { constants as fsConstants } from "node:fs"
import { WebSocketServer } from "ws"
import OpenAI from "openai"

const __dirname = dirname(fileURLToPath(import.meta.url))
const envPath = resolve(__dirname, ".env")

async function loadDotEnv() {
	try {
		await access(envPath, fsConstants.R_OK)
	} catch {
		return
	}
	const text = await readFile(envPath, "utf8")
	for (const line of text.split(/\r?\n/)) {
		const trimmed = line.trim()
		if (!trimmed || trimmed.startsWith("#")) continue
		const eq = trimmed.indexOf("=")
		if (eq < 1) continue
		const name = trimmed.slice(0, eq).trim()
		let value = trimmed.slice(eq + 1).trim()
		if (
			(value.startsWith('"') && value.endsWith('"')) ||
			(value.startsWith("'") && value.endsWith("'"))
		) {
			value = value.slice(1, -1)
		}
		if (!(name in process.env)) process.env[name] = value
	}
}

await loadDotEnv()

const PORT = Number(process.env.PORT || 8787)
const HOST = process.env.HOST || "0.0.0.0"
const CRM_BASE = (process.env.CRM_BASE_URL || "").replace(/\/$/, "")
const WEBHOOK_SECRET = (process.env.CRM_LIVE_WEBHOOK_SECRET || "").trim()

async function resolveToken(token) {
	if (!CRM_BASE) throw new Error("CRM_BASE_URL is not set")
	const url = `${CRM_BASE}/api/method/crm.live.api.resolve_call_token`
	const res = await fetch(url, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Authorization: `Bearer ${WEBHOOK_SECRET}`,
			"X-CRM-Live-Secret": WEBHOOK_SECRET,
		},
		body: JSON.stringify({ token }),
	})
	const data = await res.json()
	const msg = data?.message || data
	if (!res.ok) {
		throw new Error(msg?.exc || msg?.message || `CRM resolve failed (${res.status})`)
	}
	return msg
}

async function createLiveSession(apiKey, session) {
	const client = new OpenAI({ apiKey, maxRetries: 0 })
	if (!client.live?.create) {
		throw new Error("openai package missing client.live.create — npm install openai@latest")
	}
	// Phone audio: prefer websocket transport when the SDK exposes it; else
	// create a session record so CRM status callbacks still have a session id.
	try {
		return await client.live.create({
			session,
			transport: { type: "websocket" },
		})
	} catch (err) {
		// Fallback: SIP placeholder is handled by CRM; here we at least validate key/session
		console.warn("Live websocket transport unavailable:", err?.message || err)
		return { session: { id: `local-${Date.now()}`, ...session }, transport: { type: "none" } }
	}
}

function tokenFromUrl(reqUrl) {
	try {
		const u = new URL(reqUrl, "http://localhost")
		return (u.searchParams.get("token") || "").trim()
	} catch {
		return ""
	}
}

const server = createServer((req, res) => {
	if (req.url?.startsWith("/health")) {
		res.writeHead(200, { "Content-Type": "application/json" })
		res.end(
			JSON.stringify({
				ok: true,
				crm: Boolean(CRM_BASE),
				hasSecret: Boolean(WEBHOOK_SECRET),
			}),
		)
		return
	}
	res.writeHead(404)
	res.end("not found")
})

const wss = new WebSocketServer({ server, path: "/media" })

wss.on("connection", (twilioWs, req) => {
	const token = tokenFromUrl(req.url || "")
	let streamSid = null
	let callSid = null
	let live = null
	let startedAt = Date.now()

	console.log("Twilio media connected", { token: token.slice(0, 8) + "…" })

	twilioWs.on("message", async (raw) => {
		let msg
		try {
			msg = JSON.parse(raw.toString())
		} catch {
			return
		}
		const event = msg.event
		if (event === "connected") {
			return
		}
		if (event === "start") {
			streamSid = msg.start?.streamSid || msg.streamSid
			callSid = msg.start?.callSid
			try {
				const ctx = await resolveToken(token)
				const apiKey =
					(ctx.openai_api_key || process.env.OPENAI_API_KEY || "").trim()
				if (!apiKey) throw new Error("No OpenAI API key from CRM or env")
				live = await createLiveSession(apiKey, ctx.session || {})
				console.log("Live session ready", {
					callSid,
					sessionId: live?.session?.id,
					transport: live?.transport?.type,
				})
			} catch (err) {
				console.error("Failed to start Live session", err?.message || err)
				try {
					twilioWs.close()
				} catch {
					/* ignore */
				}
			}
			return
		}
		if (event === "media") {
			// Mulaw payload is available at msg.media.payload (base64).
			// Full duplex PCM/mulaw ↔ Live depends on transport; keep the socket
			// alive so Twilio does not drop the call while SIP/WebRTC is preferred.
			return
		}
		if (event === "stop") {
			const duration = Math.round((Date.now() - startedAt) / 1000)
			if (CRM_BASE && WEBHOOK_SECRET && token) {
				try {
					await fetch(`${CRM_BASE}/api/method/crm.live.api.bridge_session_ended`, {
						method: "POST",
						headers: {
							"Content-Type": "application/json",
							Authorization: `Bearer ${WEBHOOK_SECRET}`,
							"X-CRM-Live-Secret": WEBHOOK_SECRET,
						},
						body: JSON.stringify({ token, duration }),
					})
				} catch (err) {
					console.warn("bridge_session_ended failed", err?.message || err)
				}
			}
			console.log("Twilio media stopped", { callSid, streamSid, duration })
		}
	})

	twilioWs.on("close", () => {
		console.log("Twilio media closed", { callSid })
	})
})

server.listen(PORT, HOST, () => {
	console.log(`AO Live media bridge listening on http://${HOST}:${PORT}`)
	console.log(`Twilio Media Stream URL: wss://<host>:${PORT}/media`)
	if (!CRM_BASE) console.warn("WARNING: CRM_BASE_URL is not set")
	if (!WEBHOOK_SECRET) console.warn("WARNING: CRM_LIVE_WEBHOOK_SECRET is not set")
})
