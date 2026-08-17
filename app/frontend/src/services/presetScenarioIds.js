/**
 * Scenario labels, default questions, map bboxes, and vector-store keyword matching
 * for the impact-simulation UI. IDs match overlays seeded by general-simulation.
 */

/** Friendly labels shown in the Impact Simulation scenario picker. */
const SCENARIO_LABELS = {
  "opensky-uk-closure-001": "UK Airspace Closure",
  "supply-chain-port-strike-la": "Port Strike LA",
  "supply-chain-suez-blockage": "Suez Blockage",
};

const SCENARIO_QUESTIONS = {
  "opensky-uk-closure-001":
    "UK airspace is closed due to a NATS GPS failure. Which aircraft are affected, what diversions should be issued, and what is the estimated cost of impact?",
  "supply-chain-port-strike-la":
    "Port of Los Angeles and Long Beach are closed by a strike. Which vessels, cargo, and inland facilities are affected, and what is the estimated cost of impact?",
  "supply-chain-suez-blockage":
    "The Suez Canal is blocked. Which vessels and cargoes are delayed, what is the impact on European ports, and what is the estimated cost of impact?",
};

/** Default Impact Query question shown before any scenario is selected. */
export const DEFAULT_IMPACT_QUESTION = SCENARIO_QUESTIONS["opensky-uk-closure-001"];

/** Short, clickable prompts a user can run for each scenario. */
export const SCENARIO_SUGGESTED_PROMPTS = {
  "opensky-uk-closure-001": [
    "Show affected aircraft and recommend diversions.",
    "Which airports and fleets are impacted by the closure?",
    "Estimate the cost and value at risk of the disruption.",
  ],
  "supply-chain-port-strike-la": [
    "Show affected vessels, cargo, and inland facilities.",
    "Recommend alternative ports and mitigation routes.",
    "Estimate the cost and value at risk of the strike.",
  ],
  "supply-chain-suez-blockage": [
    "Show vessels and cargo delayed by the blockage.",
    "What is the impact on European ports and schedules?",
    "Estimate the cost and value at risk of the blockage.",
  ],
};

/** Suggested prompt chips for a scenario; empty when the scenario is not preset. */
export function suggestedPromptsForScenario(scenarioId) {
  return SCENARIO_SUGGESTED_PROMPTS[scenarioId] || [];
}

/** Map bboxes (minLon,minLat,maxLon,maxLat) focused on each scenario. */
const SCENARIO_BBOXES = {
  "opensky-uk-closure-001": "-15,35,40,62",
  "supply-chain-port-strike-la": "-130,30,-110,40",
  "supply-chain-suez-blockage": "0,20,50,55",
};

/**
 * Always-on news store; never auto-selected as a scenario's RAG knowledge base.
 * Its name is kept in sync with `news_vector_store_service._NEWS_VECTOR_STORE_NAME`.
 */
const NEWS_VECTOR_STORE_NAME = "supply-chain-news";

/**
 * Keywords matched against Llama Stack vector-store names when a scenario is
 * selected. Augmented with tokens from the scenario label and id, so
 * user-uploaded knowledge bases with descriptive names match reliably.
 */
const SCENARIO_VECTOR_STORE_KEYWORDS = {
  "opensky-uk-closure-001": [
    "uk",
    "nats",
    "gps",
    "air",
    "airspace",
    "flight",
    "aviation",
    "aircraft",
    "opensky",
    "closure",
  ],
  "supply-chain-port-strike-la": [
    "port",
    "strike",
    "la",
    "los",
    "angeles",
    "long",
    "beach",
    "vessel",
    "cargo",
    "shipping",
  ],
  "supply-chain-suez-blockage": ["suez", "canal", "blockage", "block", "vessel", "shipping", "egypt"],
};

/** Generic words derived from scenario ids that should not drive KB matching. */
const SCENARIO_KEYWORD_STOPWORDS = new Set([
  "supply",
  "chain",
  "scenario",
  "demo",
  "impact",
  "data",
  "simulation",
  "news",
]);

/** Broad envelope covering all seeded demo entities. */
export const GLOBAL_DEMO_BBOX = "-130,20,50,62";

export function labelForScenario(scenarioId) {
  if (!scenarioId) return "";
  if (SCENARIO_LABELS[scenarioId]) {
    return SCENARIO_LABELS[scenarioId];
  }
  return humanizeScenarioId(scenarioId);
}

/** Turn ``france-airspace-closure`` into ``France Airspace Closure``. */
export function humanizeScenarioId(scenarioId) {
  return String(scenarioId)
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

export function questionForScenario(scenarioId) {
  if (SCENARIO_QUESTIONS[scenarioId]) {
    return SCENARIO_QUESTIONS[scenarioId];
  }
  const label = labelForScenario(scenarioId);
  return (
    `${label} is active. Which entities are affected, what diversions or mitigations ` +
    "should be issued, and what is the estimated cost of impact?"
  );
}

export function bboxForScenario(scenarioId) {
  return SCENARIO_BBOXES[scenarioId] || GLOBAL_DEMO_BBOX;
}

/** Keywords used to select a vector store for *scenarioId*. */
function vectorStoreKeywordsForScenario(scenarioId) {
  const explicit = SCENARIO_VECTOR_STORE_KEYWORDS[scenarioId] || [];
  const labelTokens = normalizeTokens(labelForScenario(scenarioId));
  const idTokens = normalizeTokens(scenarioId);
  const seen = new Set();
  const resolved = [];
  for (const raw of [...explicit, ...labelTokens, ...idTokens]) {
    const kw = String(raw || "").toLowerCase().trim();
    if (!kw || seen.has(kw)) continue;
    if (SCENARIO_KEYWORD_STOPWORDS.has(kw)) continue;
    if (/^\d{2,}$/.test(kw)) continue; // numeric id segments (e.g. "001")
    seen.add(kw);
    resolved.push(kw);
  }
  return resolved;
}

/** Split a name/id into lowercase alphanumeric tokens. */
function normalizeTokens(value) {
  return String(value || "")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

/**
 * Best vector-store id for a scenario: the store whose name covers the most
 * keywords. Prefers full coverage; falls back to the highest partial score.
 */
function findVectorStoreId(stores, keywords) {
  if (!Array.isArray(stores) || keywords.length === 0) {
    return "";
  }
  let bestId = "";
  let bestScore = 0;
  for (const store of stores) {
    const name = store.name || store.id || "";
    if (name.toLowerCase().includes(NEWS_VECTOR_STORE_NAME)) {
      continue;
    }
    const tokens = normalizeTokens(name);
    let score = 0;
    for (const kw of keywords) {
      // Exact token match, or prefix match for meaningful (>=3 char) keywords
      // (e.g. "air" -> "airspace"); short keywords like "la" must match exactly.
      const match = (token) =>
        token === kw || (kw.length >= 3 && token.startsWith(kw));
      if (tokens.some(match)) {
        score += 1;
      }
    }
    if (score > bestScore) {
      bestScore = score;
      bestId = store.id || store.vector_store_id || "";
    }
  }
  return bestScore > 0 ? bestId : "";
}

export function findVectorStoreIdForScenario(stores, scenarioId) {
  return findVectorStoreId(stores, vectorStoreKeywordsForScenario(scenarioId));
}

/** Display name of the vector store matched to a scenario, or empty when none. */
export function findVectorStoreNameForScenario(stores, scenarioId) {
  const id = findVectorStoreIdForScenario(stores, scenarioId);
  if (!id || !Array.isArray(stores)) {
    return "";
  }
  const store = stores.find((row) => (row.id || row.vector_store_id) === id);
  return (store?.name || "").trim();
}
