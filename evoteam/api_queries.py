"""HTTP read adapters. SQLite mode=ro prevents writes, even by accident."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from evoteam.domain.run import RunPurpose
from evoteam.presentation.models import EvidenceEnvelope
from evoteam.presentation.projections import redact, run_detail, strategy_view, summary
from evoteam.storage.sqlite import SQLiteStorage, StoragePorts


@asynccontextmanager
async def read_ports(database: Path) -> AsyncIterator[StoragePorts]:
    if not database.is_file():
        raise HTTPException(503, "证据数据库尚未准备好；请先配置已有数据库")
    storage = SQLiteStorage(f"sqlite:///{database.resolve().as_uri()}?mode=ro&uri=true")
    try:
        yield await storage.open()
    except KeyError as exc:
        raise HTTPException(404, "该记录不存在") from exc
    except ValueError as exc:
        raise HTTPException(400, "查询参数无效，或数据库需要显式迁移") from exc
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(503, "证据数据库暂时不可读取") from exc
    finally:
        await storage.close()


def create_query_router(database: Path) -> APIRouter:
    router = APIRouter(prefix="/v1", tags=["只读证据"])

    @router.get("/runs", response_model=EvidenceEnvelope)
    async def runs(
        strategy_id: Annotated[str, Query(min_length=1, max_length=128)],
        purpose: RunPurpose | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        cursor: str | None = None,
    ) -> EvidenceEnvelope:
        async with read_ports(database) as ports:
            items, next_cursor = await ports.runs.list_runs(
                strategy_id, purpose=purpose, limit=limit, cursor=cursor
            )
            return EvidenceEnvelope(
                data={"items": [summary(r) for r in items], "next_cursor": next_cursor}
            )

    @router.get("/runs/{run_id}", response_model=EvidenceEnvelope)
    async def detail(run_id: str) -> EvidenceEnvelope:
        async with read_ports(database) as ports:
            data, missing = await run_detail(ports.runs, run_id)
            return EvidenceEnvelope(data=data, missing_refs=missing)

    async def event_data(ports: StoragePorts, run_id: str) -> list[dict[str, Any]]:
        await ports.runs.get_sealed_run(run_id)
        events = await ports.runs.events_for_run(run_id)
        return [redact(e.model_dump(mode="json", exclude={"payload"})) for e in events]

    @router.get("/runs/{run_id}/events", response_model=EvidenceEnvelope)
    async def events(run_id: str) -> EvidenceEnvelope:
        async with read_ports(database) as ports:
            return EvidenceEnvelope(data={"items": await event_data(ports, run_id)})

    @router.get("/runs/{run_id}/export")
    async def export(run_id: str) -> JSONResponse:
        async with read_ports(database) as ports:
            data, missing = await run_detail(ports.runs, run_id)
            data["events"] = await event_data(ports, run_id)
            envelope = EvidenceEnvelope(data=data, missing_refs=missing)
            return JSONResponse(
                envelope.model_dump(mode="json"),
                headers={"Content-Disposition": 'attachment; filename="evoteam-run-evidence.json"'},
            )

    @router.get("/strategies/{strategy_id}/versions", response_model=EvidenceEnvelope)
    async def versions(strategy_id: str) -> EvidenceEnvelope:
        async with read_ports(database) as ports:
            items = await ports.strategies.list_versions(strategy_id)
            if not items:
                raise HTTPException(404, "策略不存在")
            current = None
            try:
                current = (await ports.strategies.current(strategy_id)).metadata.ref.model_dump(
                    mode="json"
                )
            except KeyError:
                pass
            return EvidenceEnvelope(
                data={"items": [strategy_view(s) for s in items], "current": current},
                missing_refs=[] if current else ["current_strategy"],
            )

    @router.get("/evolutions", response_model=EvidenceEnvelope)
    async def evolutions(
        strategy_id: Annotated[str, Query(min_length=1, max_length=128)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        cursor: str | None = None,
    ) -> EvidenceEnvelope:
        async with read_ports(database) as ports:
            items, next_cursor = await ports.evolutions.list_records(
                strategy_id, limit=limit, cursor=cursor
            )
            return EvidenceEnvelope(
                data={
                    "items": [redact(r.model_dump(mode="json")) for r in items],
                    "next_cursor": next_cursor,
                }
            )

    @router.get("/evolutions/{evolution_id}", response_model=EvidenceEnvelope)
    async def evolution(evolution_id: str) -> EvidenceEnvelope:
        async with read_ports(database) as ports:
            record = await ports.evolutions.get_record(evolution_id)
            data: dict[str, Any] = {"record": record.model_dump(mode="json")}
            missing: list[str] = []
            for key, refs, getter in (
                ("attributions", record.attribution_refs, ports.evolutions.get_attribution),
                ("proposals", record.proposal_refs, ports.evolutions.get_proposal),
                ("validations", record.validation_refs, ports.evolutions.get_validation),
            ):
                data[key] = []
                for ref in refs:
                    try:
                        data[key].append((await getter(ref)).model_dump(mode="json"))
                    except KeyError:
                        missing.append(f"{key}:{ref}")
            data["strategies"] = []
            for ref in (record.trigger.strategy, *record.candidates):
                try:
                    data["strategies"].append(strategy_view(await ports.strategies.get(ref)))
                except KeyError:
                    missing.append(f"strategy:{ref.strategy_id}@{ref.version}")
            return EvidenceEnvelope(data=redact(data), missing_refs=missing)

    return router
