/** One-line summary for token counts and model from a serialized chat completion. */
export function formatCompletionSummary(completion) {
  if (!completion || typeof completion !== "object") {
    return "";
  }
  const usage = completion.usage;
  const model = typeof completion.model === "string" ? completion.model : undefined;
  const choices = Array.isArray(completion.choices) ? completion.choices : [];
  const finish = choices[0] && typeof choices[0] === "object" ? choices[0].finish_reason : undefined;

  const parts = [];
  if (usage && typeof usage === "object") {
    const total = usage.total_tokens;
    const prompt = usage.prompt_tokens;
    const comp = usage.completion_tokens;
    if (typeof total === "number") {
      const inTok = typeof prompt === "number" ? prompt : "—";
      const outTok = typeof comp === "number" ? comp : "—";
      parts.push(`${total} tokens (in ${inTok} · out ${outTok})`);
    }
  }
  if (model) {
    parts.push(`model ${model}`);
  }
  if (typeof finish === "string" && finish) {
    parts.push(`finish ${finish}`);
  }
  return parts.join(" · ");
}
