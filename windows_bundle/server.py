"""Windows entry point for the SmartSchool Vision control plane."""

import argparse
from multiprocessing import freeze_support
from pathlib import Path

from windows_bundle.runtime import (
    BUNDLE_ROOT, LOOPBACK, default_data_dir, enter_data_dir, stage_license_notices, stage_web_assets,
)


def serve() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--port", type=int, default=8005)
    args = parser.parse_args()
    state = enter_data_dir(args.data_dir)
    stage_web_assets(BUNDLE_ROOT, state)
    stage_license_notices("server", state)

    import uvicorn
    from main import app

    uvicorn.run(app, host=LOOPBACK, port=args.port, loop="asyncio", http="h11",
                ws="websockets", lifespan="on")


if __name__ == "__main__":
    freeze_support()
    serve()
