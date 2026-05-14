"""JSON store modules (knowledge bases + simulations)."""

from services.knowledge_bases_store import new_record_stub


def test_knowledge_bases_append_and_load(knowledge_bases_store_module):
    kb = knowledge_bases_store_module
    assert kb.load_all() == []
    row = new_record_stub(name="A", vector_store_id="vs1", files_meta=[])
    kb.append_record(row)
    loaded = kb.load_all()
    assert len(loaded) == 1
    assert loaded[0]["name"] == "A"


def test_simulations_append_and_load(simulations_store_module):
    sim = simulations_store_module
    assert sim.load_all() == []
    rec = sim.append_simulation("  Scenario X  ", "desc")
    assert rec["name"] == "Scenario X"
    assert sim.load_all()[0]["id"] == rec["id"]
