/** Sample general-simulation QueryResponse for UI tests. */
export const QUERY_RESPONSE_FIXTURE = {
  question: "What is affected?",
  scenario_id: "opensky-uk-closure-001",
  answer: "Three aircraft are affected by the UK airspace closure.",
  affected_entities: ["opensky-407290", "opensky-471f52", "cargo-opensky-407290-1"],
  solver: {
    affected_count: 3,
    max_chain_length: 2,
    impact_score: 0.65,
    total_value_at_risk: 1234567,
    currency: "USD",
    value_breakdown: [{ entity_id: "opensky-407290", value_usd: 620000 }],
    response_options: [
      {
        rank: 1,
        label: "emergency_response",
        description: "Isolate and divert immediately.",
        estimated_impact_reduction: 0.8,
      },
    ],
    recommended_reroutes: [
      {
        entity_id: "opensky-407290",
        target_id: "EIDW",
        target_label: "Dublin (EIDW)",
        latitude: 53.4213,
        longitude: -6.2701,
        rationale: "Divert while disruption is active.",
      },
    ],
    explanation: "StubSolver analysis",
  },
  tool_call_trace: [
    {
      tool_name: "solve_impact",
      arguments: { scenario_id: "opensky-uk-closure-001" },
      output: { success: true, impact_score: 0.65 },
    },
  ],
};
