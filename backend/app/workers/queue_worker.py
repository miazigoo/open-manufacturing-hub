from __future__ import annotations

import argparse
import asyncio
import logging
import socket

from sqlalchemy import text

from app.core.database import async_session
from app.core.config import get_settings
from app.core.enums import HealthComponentType, HealthStatus
from app.health.models import HealthCheck
from app.workers.runner import process_batch, process_once

logger = logging.getLogger("omh.worker.queue")


async def _run_once(worker: str) -> int:
    async with async_session() as session:
        item = await process_once(session, worker=worker)
        await session.commit()
        return 1 if item else 0


async def _run_batch(worker: str, limit: int) -> int:
    async with async_session() as session:
        items = await process_batch(session, limit=limit, worker=worker)
        await session.commit()
        return len(items)


async def _heartbeat(worker: str, *, processed: int, status: HealthStatus = HealthStatus.OK) -> None:
    async with async_session() as session:
        session.add(
            HealthCheck(
                component_type=HealthComponentType.AGENT,
                component_name="queue-worker",
                status=status,
                details_json={"worker": worker, "processed": processed},
            )
        )
        await session.commit()


async def _healthcheck() -> None:
    async with async_session() as session:
        await session.execute(text("SELECT 1"))


async def _loop(worker: str, limit: int, interval: float) -> None:
    logger.warning("Queue worker started: worker=%s batch_limit=%s interval=%ss", worker, limit, interval)
    while True:
        try:
            processed = await _run_batch(worker, limit)
            await _heartbeat(worker, processed=processed)
            logger.info("Queue worker cycle: worker=%s processed=%s", worker, processed)
        except Exception as exc:
            logger.exception("Queue worker cycle failed: worker=%s error=%s", worker, exc)
            await _heartbeat(worker, processed=0, status=HealthStatus.WARNING)
        await asyncio.sleep(interval)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Process OMH integration queue items")
    parser.add_argument("--worker", default=f"queue-worker-{socket.gethostname()}")
    parser.add_argument("--once", action="store_true", help="Process one item and exit")
    parser.add_argument("--batch", action="store_true", help="Process one batch and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously. This is the default when no mode is provided.")
    parser.add_argument("--healthcheck", action="store_true", help="Check database connectivity and exit")
    parser.add_argument("--limit", type=int, default=get_settings().queue_worker_batch_size)
    parser.add_argument("--interval", type=float, default=get_settings().queue_worker_loop_interval_seconds)
    args = parser.parse_args()
    if args.healthcheck:
        await _healthcheck()
        print("ok")
        return
    if args.once:
        processed = await _run_once(args.worker)
    elif args.batch:
        processed = await _run_batch(args.worker, args.limit)
    else:
        await _loop(args.worker, args.limit, args.interval)
        return
    await _heartbeat(args.worker, processed=processed)
    print(f"processed={processed}")


if __name__ == "__main__":
    asyncio.run(main())
