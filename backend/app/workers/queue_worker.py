from __future__ import annotations

import argparse
import asyncio
import socket

from app.core.database import async_session
from app.core.config import get_settings
from app.workers.runner import process_batch, process_once


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


async def main() -> None:
    parser = argparse.ArgumentParser(description="Process OMH integration queue items")
    parser.add_argument("--worker", default=f"queue-worker-{socket.gethostname()}")
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--limit", type=int, default=get_settings().queue_worker_batch_size)
    args = parser.parse_args()
    processed = await (_run_batch(args.worker, args.limit) if args.batch else _run_once(args.worker))
    print(f"processed={processed}")


if __name__ == "__main__":
    asyncio.run(main())
