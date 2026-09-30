import Anthropic from "@anthropic-ai/sdk";
import { config } from "./config.js";

let client = null;
function getClient() {
  if (!client) client = new Anthropic({ apiKey: config.anthropicApiKey });
  return client;
}

/**
 * Ask Claude for a reply.
 *
 * @param {object} opts
 * @param {import("@anthropic-ai/sdk").Anthropic.Beta.BetaMessageParam[]} opts.history  prior turns
 * @param {import("@anthropic-ai/sdk").Anthropic.Beta.BetaContentBlockParam[]|string} opts.userContent  this turn
 * @param {string} [opts.extraSystem]  situational context appended to the system prompt (not cached)
 * @returns {Promise<{text: string, refused: boolean}>}
 */
export async function askClaude({ history, userContent, extraSystem }) {
  const system = [
    { type: "text", text: config.systemPrompt, cache_control: { type: "ephemeral" } },
  ];
  if (extraSystem) system.push({ type: "text", text: extraSystem });

  const response = await getClient().beta.messages.create({
    model: config.model,
    max_tokens: config.maxTokens,
    system,
    messages: [...history, { role: "user", content: userContent }],
    output_config: { effort: config.effort },
    // Server-side fallback: if the model declines for policy reasons, the API retries the same
    // request on Anthropic's default substitute model inside the same call.
    betas: ["server-side-fallback-2026-07-01"],
    fallbacks: "default",
  });

  if (response.stop_reason === "refusal") {
    const why = response.stop_details?.explanation;
    return { text: why ? `I can't help with that. (${why})` : "I can't help with that.", refused: true };
  }

  const text = response.content
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("\n")
    .trim();

  return { text: text || "(no reply)", refused: false };
}

/** Map SDK errors to a short, user-safe message. */
export function describeError(err) {
  if (err instanceof Anthropic.AuthenticationError) return "Claude API key is invalid.";
  if (err instanceof Anthropic.RateLimitError) return "Claude is rate limited right now, try again in a moment.";
  if (err instanceof Anthropic.BadRequestError) return `Claude rejected the request: ${err.message}`;
  if (err instanceof Anthropic.APIConnectionError) return "Could not reach the Claude API.";
  if (err instanceof Anthropic.APIError) return `Claude API error ${err.status}: ${err.message}`;
  return `Unexpected error: ${err?.message || err}`;
}
