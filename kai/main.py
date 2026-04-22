"""Entry point. Run with `python -m kai.main`."""
from __future__ import annotations
import asyncio
import signal
import sys

from .kai import Kai
from .logger import logger


async def _amain() -> int:
    try:
        kai = Kai()
    except EnvironmentError as e:
        logger.error("main", f"config invalid: {e}")
        return 2

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal(sig_name: str):
        logger.info("main", f"signal {sig_name} received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal, sig.name)
        except NotImplementedError:
            pass

    runner = asyncio.create_task(kai.run())
    waiter = asyncio.create_task(stop_event.wait())
    done, pending = await asyncio.wait({runner, waiter}, return_when=asyncio.FIRST_COMPLETED)

    if waiter in done:
        runner.cancel()
        try:
            await runner
        except asyncio.CancelledError:
            pass

    await kai.shutdown_mgr.shutdown("signal")
    return 0


def main() -> None:
    try:
        rc = asyncio.run(_amain())
    except KeyboardInterrupt:
        rc = 0
    sys.exit(rc)


if __name__ == "__main__":
    main()
