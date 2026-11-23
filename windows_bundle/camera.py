"""Windows entry point for the SmartSchool Vision camera service."""

import argparse
import asyncio
from multiprocessing import freeze_support
from pathlib import Path

from windows_bundle.runtime import (
    LOOPBACK, default_data_dir, enter_data_dir, resolve_video_source, stage_license_notices,
)


async def run_camera(source: str | None, port: int, server_port: int) -> None:
    from config import settings
    from database import create_session, destroy_session, init_db
    from аи import gg

    await init_db()
    token = await create_session("Local camera", "camera", gg.CAMERA_ID)
    try:
        await gg.main(
            source=source, stream_host=LOOPBACK, stream_port=port,
            server_url=f"ws://{LOOPBACK}:{server_port}/ws",
            server_headers={"Cookie": f"{settings.session_cookie_name}={token}"},
        )
    finally:
        await destroy_session(token)


def start() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--video", help="Loop a recorded video instead of opening webcams")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--server-port", type=int, default=8005)
    args = parser.parse_args()
    try:
        source = resolve_video_source(args.video)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    state = enter_data_dir(args.data_dir)
    stage_license_notices("camera", state)

    from dotenv import load_dotenv
    load_dotenv(Path(".env"), override=False)
    asyncio.run(run_camera(source, args.port, args.server_port))


if __name__ == "__main__":
    freeze_support()
    start()
