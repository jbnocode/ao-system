/**
 * Local-only GPT-Live-1 demo (direct OpenAI, no Vapi).
 * Browser posts an SDP offer; server creates a Live WebRTC session.
 *
 *   export OPENAI_API_KEY=sk-...
 *   # or put OPENAI_API_KEY=sk-... in .env next to this file
 *   npm start
 *   open http://localhost:3000
 */
import express from "express"
import OpenAI from "openai"
import { readFile, access } from "node:fs/promises"
import { resolve, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { constants as fsConstants } from "node:fs"

const __dirname = dirname(fileURLToPath(import.meta.url))
const port = Number(process.env.PORT || 3000)
const origin = `http://localhost:${port}`
const indexPath = resolve(__dirname, "index.html")
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

// Demo-style speaker prompt — closer to OpenAI's marketing "try it" session
// than a stiff insurance script. Goal: judge conversational nuance.
const SPEAKER_INSTRUCTIONS = `You are a calm, friendly voice companion for a product demo.
Speak warmly and naturally, at an unhurried pace. Be clear and direct, not overly cheerful or salesy.
Sound like a real person on a call — vary phrasing, it's fine to hesitate briefly ("hmm") when thinking.

Backchannel policy: Use moderate backchannels ("mm-hmm", "yeah", "got it") while the user talks. Acknowledge naturally without competing with their turn.

Interruption policy: Stop speaking the moment they interrupt. Listen to what they say. Don't finish the old sentence. Don't apologize every time — just follow their new direction.

Silence & noise policy: Keep listening while they pause to think. Do not jump in on short silences. Ignore coughs, music, traffic, or nearby conversation unless they clearly address you again.

If they laugh, change their mind mid-sentence, or talk aside briefly, stay with them and continue naturally.

For routine replies, use one or two short spoken sentences, then listen.

Delegation policy:
Backend tools:
- Web search: look up current facts when needed.

Generate <|SpawnThinking|> when:
- The request needs current information or careful reasoning beyond a simple reply.

Do not generate <|SpawnThinking|> when:
- Greetings, small talk, repeats, or simple clarifications from the conversation.

Generate <|SpawnThinking|> before giving an answer that depends on backend work.
Do not guess the result while waiting.`

const REASONER_INSTRUCTIONS = `Use web search when current facts are needed.
Return concise, grounded results for a spoken conversation (1–2 short sentences worth of content).
Never invent facts.`

function assertOpenAiKey() {
	const key = (process.env.OPENAI_API_KEY || "").trim()
	if (!key) {
		return {
			ok: false,
			error:
				"OPENAI_API_KEY is not set. Export a real OpenAI key (sk-… / sk-proj-…). CRM AI Settings currently holds a Bedrock key, which will not work here.",
		}
	}
	if (!(key.startsWith("sk-") || key.startsWith("sk-proj-"))) {
		return {
			ok: false,
			error:
				"OPENAI_API_KEY does not look like an OpenAI secret key (expected sk-…). A Bedrock/AWS key will return 401/502.",
		}
	}
	return { ok: true, key }
}

const keyCheck = assertOpenAiKey()
const app = express()
const client = keyCheck.ok
	? new OpenAI({ apiKey: keyCheck.key, maxRetries: 0 })
	: null

app.use(express.json({ limit: "64kb" }))

app.get("/", async (_req, res) => {
	res.type("html").send(await readFile(indexPath, "utf8"))
})

app.get("/health", (_req, res) => {
	const check = assertOpenAiKey()
	res.json({
		ok: check.ok,
		hasKey: Boolean(process.env.OPENAI_API_KEY),
		keyLooksOpenAi: check.ok,
		hasLiveApi: Boolean(client?.live?.create),
		model: "gpt-live-1",
		path: "direct-openai",
		hint: check.ok ? undefined : check.error,
	})
})

// Local-only demo. Add auth before exposing beyond localhost.
app.post("/api/session", async (req, res) => {
	if (req.headers.origin && req.headers.origin !== origin) {
		res.status(403).json({ error: "Unexpected request origin" })
		return
	}
	if (typeof req.body?.sdp !== "string" || !req.body.sdp.trim()) {
		res.status(400).json({ error: "An SDP offer is required" })
		return
	}

	const check = assertOpenAiKey()
	if (!check.ok || !client?.live?.create) {
		res.status(503).json({
			error:
				check.error ||
				"OpenAI SDK is missing client.live.create — run npm install openai@latest",
		})
		return
	}

	try {
		const result = await client.live.create({
			session: {
				model: "gpt-live-1",
				instructions: SPEAKER_INSTRUCTIONS,
				delegation: {
					type: "responses",
					responses: {
						model: "gpt-5.6-terra",
						instructions: REASONER_INSTRUCTIONS,
						tools: [{ type: "web_search" }],
						tool_choice: "auto",
					},
				},
			},
			transport: {
				type: "webrtc",
				sdp: req.body.sdp,
			},
		})
		res.status(201).json(result)
	} catch (error) {
		const status = error?.status ?? 502
		const detail =
			error?.error?.message || error?.message || "Live session creation failed"
		console.error("Live session creation failed", status, detail)
		res.status(typeof status === "number" ? status : 502).json({ error: detail })
	}
})

app.listen(port, "127.0.0.1", () => {
	console.log(`AO GPT-Live direct demo → ${origin}`)
	console.log("A/B: this page vs Vapi web call / +1 (912) 766-9359")
	if (!assertOpenAiKey().ok) {
		console.warn("WARNING:", assertOpenAiKey().error)
	}
})
