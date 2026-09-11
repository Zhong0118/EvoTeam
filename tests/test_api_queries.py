"""The workbench only reads existing evidence; it never creates a database."""

import asyncio
from typing import Any

from fastapi.testclient import TestClient

from evoteam.api import create_app
from evoteam.demo import run_demo
from evoteam.settings import Settings


def client_for(path):
    return TestClient(
        create_app(Settings(**dict[str, Any](_env_file=None, database_url=f"sqlite:///{path}")))
    )


def test_queries_do_not_create_missing_database(tmp_path):
    path = tmp_path / "missing.sqlite3"
    with client_for(path) as client:
        assert client.get("/v1/runs?strategy_id=demo").status_code == 503
    assert not path.exists()


def test_read_evidence_and_export_without_writes(tmp_path):
    path = tmp_path / "evidence #1?.sqlite3"
    seed = tmp_path / "seed.sqlite3"
    sealed = asyncio.run(run_demo(seed))
    seed.rename(path)
    before = path.read_bytes()
    with client_for(path) as client:
        listing = client.get("/v1/runs?strategy_id=demo-project-planning").json()
        assert listing["source_kind"] == "current_database"
        assert listing["data"]["items"][0]["run_id"] == sealed.run_id
        assert listing["data"]["next_cursor"] is None
        detail = client.get(f"/v1/runs/{sealed.run_id}").json()
        assert detail["data"]["plan"]["schedule"]
        assert detail["data"]["nodes"][0]["role"] == "planner"
        events = client.get(f"/v1/runs/{sealed.run_id}/events").json()["data"]["items"]
        assert events and events == sorted(events, key=lambda e: e["sequence"])
        assert all("payload" not in item for item in events)
        states = {e["event_type"]: e["node_state"] for e in events}
        assert states["agent_started"] == "running"
        assert states["agent_completed"] == "completed"
        assert states["run_finished"] is None
        team = next(e for e in events if e["event_type"] == "team_created")
        assert team["config"]["enabled_nodes"] == ["planner", "executor", "critic"]
        completed = [e for e in events if e["event_type"] == "agent_completed"]
        assert any(e["output"] and "summary" in e["output"] for e in completed)
        assert any(e["output"] and e["output"].get("schedule") for e in completed)
        assert any(e["output"] and "passed" in e["output"] for e in completed)
        export = client.get(f"/v1/runs/{sealed.run_id}/export")
        assert export.status_code == 200
        assert "attachment" in export.headers["content-disposition"]
        assert "snapshot_ref" not in export.text
        assert str(tmp_path) not in export.text
        versions = client.get("/v1/strategies/demo-project-planning/versions").json()["data"]
        assert versions["current"]["version"] == 0
        assert client.get("/v1/runs/no-such-run").status_code == 404
        assert client.get("/v1/runs/no-such-run/events").status_code == 404
        assert client.get("/v1/runs?strategy_id=demo&limit=0").status_code == 422
        assert client.get("/v1/runs?strategy_id=demo&cursor=bad").status_code == 400
        assert (
            client.get("/v1/runs?strategy_id=demo-project-planning&purpose=validation").json()[
                "data"
            ]["items"]
            == []
        )
        assert (
            client.get("/v1/evolutions?strategy_id=demo-project-planning").json()["data"]["items"]
            == []
        )
    assert before == path.read_bytes()


def test_partial_evolution_returns_missing_refs(tmp_path):
    from evoteam.domain.common import AssetRef
    from evoteam.domain.evolution import EvolutionRecord, EvolutionTrigger, TriggerType
    from evoteam.storage.sqlite import SQLiteStorage

    path = tmp_path / "partial.sqlite3"
    sealed = asyncio.run(run_demo(path))

    async def add_record():
        storage = SQLiteStorage(f"sqlite:///{path}")
        try:
            ports = await storage.open()
            await ports.evolutions.save_record(
                EvolutionRecord(
                    evolution_id="partial",
                    trigger=EvolutionTrigger(
                        trigger_id="trigger",
                        strategy=sealed.strategy,
                        policy_ref=AssetRef(id="test-policy", version="1"),
                        trigger_type=TriggerType.REPEATED_FAILURE,
                        task_scope="project_planning",
                        evidence_run_ids=(sealed.run_id,),
                        reason="test",
                    ),
                    attribution_refs=("missing-attribution",),
                    proposal_refs=("missing-proposal",),
                    validation_refs=("missing-validation",),
                )
            )
        finally:
            await storage.close()

    asyncio.run(add_record())
    before = path.read_bytes()
    with client_for(path) as client:
        response = client.get("/v1/evolutions/partial")
        assert response.status_code == 200
        data = response.json()
        assert len(data["missing_refs"]) == 3
        assert data["data"]["record"]["promoted"] is None
        assert data["data"]["validations"] == []
    assert before == path.read_bytes()


def test_projection_omits_credentials_paths_and_connection_fields():
    from evoteam.presentation.projections import redact

    value = redact(
        {
            "api_key": "do-not-export",
            "context": {"secret": "hidden"},
            "output": "Bearer private-token sk-private /Users/alice/local.env https://model.test/key",
            "tokens": None,
        }
    )
    assert redact("task-project-planning") == "task-project-planning"
    assert value["tokens"] is None
    assert "api_key" not in value
    assert "context" not in value
    assert "private-token" not in value["output"]
    assert "/Users/" not in value["output"]
    assert "https://" not in value["output"]
