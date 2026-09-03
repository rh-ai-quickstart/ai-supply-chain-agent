"""Seed preset SimulationEvent nodes in Neo4j for Kind UI E2E smoke tests.

Writes directly to Neo4j (no vector DB / Llama Stack) so this works when
general-simulation.llama-stack is disabled in values-kind.yaml.

Run inside the general-sim-api pod (neo4j driver + NEO4J_* env are present):

    kubectl exec -i deploy/general-sim-api -n <ns> -- python - < scripts/ci/kind-seed-demo-scenarios.py
"""
from __future__ import annotations

import asyncio
import os
import sys

from neo4j import AsyncGraphDatabase

# IDs and labels match app/frontend/src/services/presetScenarioIds.js and
# general-simulation/scripts/seed_demo.py.
SCENARIOS = [
    (
        "evt-uk-airspace-closure-20260630",
        "opensky-uk-closure-001",
        "UK airspace closed due to NATS GPS failure",
        "-15,35,40,62",
    ),
    (
        "evt-port-strike-la-2026",
        "supply-chain-port-strike-la",
        "Port strike at Los Angeles and Long Beach",
        "-130,30,-110,40",
    ),
    (
        "evt-suez-blockage-2026",
        "supply-chain-suez-blockage",
        "Suez Canal blockage",
        "0,20,50,55",
    ),
]


async def main() -> None:
    uri = os.environ.get("NEO4J_URI", "").strip()
    password = os.environ.get("NEO4J_PASSWORD", "").strip()
    user = os.environ.get("NEO4J_USER", "neo4j").strip() or "neo4j"
    if not uri or not password:
        print("NEO4J_URI and NEO4J_PASSWORD must be set", file=sys.stderr)
        raise SystemExit(1)

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session(database="neo4j") as session:
            for event_id, scenario_id, description, bbox in SCENARIOS:
                await session.run(
                    "MERGE (e:SimulationEvent {id: $id}) "
                    "SET e.scenario_id = $scenario_id, "
                    "    e.description = $description, "
                    "    e.affect_bbox = $bbox",
                    id=event_id,
                    scenario_id=scenario_id,
                    description=description,
                    bbox=bbox,
                )
                print(f"seeded {scenario_id}", flush=True)
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
