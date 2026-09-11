from __future__ import annotations

import asyncio
import os
import signal

from app.services.strategic_agents.scheduled_runner import (
    strategic_agent_scheduled_runner,
)


async def run_worker() -> None:
    """Run strategic-agent scheduling outside the FastAPI web process."""
    # A dedicated worker should own scheduled execution. Keep the API process
    # responsive by running this module as a separate service/process.
    os.environ.setdefault("STRATEGIC_AGENT_SCHEDULER_ENABLED", "true")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            # Signal handlers are not available on every event-loop platform.
            pass

    await strategic_agent_scheduled_runner.start()

    try:
        await stop_event.wait()
    finally:
        await strategic_agent_scheduled_runner.stop()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
