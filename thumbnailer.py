#!/usr/bin/env python3

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta
import time
import logging
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from typing import NamedTuple

TOPAZ = Path("/Applications/Topaz Video AI.app").absolute()
FFMPEG = TOPAZ / "Contents/MacOS/ffmpeg"
TOPAZ_MODEL_DIR = TOPAZ / "Contents/Resources/models"
TOPAZ_ENV_VARS = {
    "TVAI_MODEL_DIR": str(TOPAZ_MODEL_DIR),
    "TVAI_MODEL_DATA_DIR": str(TOPAZ_MODEL_DIR),
}
LOG_DIR = (
    Path(__file__).parent.absolute() / "thumbnailer-logs" / datetime.now().isoformat()
)

# 32 is INFO
FFMPEG_LOG_LEVEL = 32
MAX_THREADS = 2


class Command(NamedTuple):
    name: str
    output: Path
    commands: tuple[tuple[str, ...], ...]


logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def stabilize_and_apply_lut(*, input_video_path: Path, lut_path: Path):
    logging.info(f"[{input_video_path}] Starting")
    stabilized_video_path = input_video_path.with_name(
        re.sub(r"\..*?$", r"_thumbnailer_stab\g<0>", input_video_path.name)
    )
    proxy_video_path = input_video_path.with_name(
        re.sub(r"\..*?$", r"_Proxy\g<0>", input_video_path.name)
    )
    preview_video_path = input_video_path.with_name(
        re.sub(r"\..*?$", r"_thumbnailer_preview\g<0>", input_video_path.name)
    )

    ffmpeg_args = (
        str(FFMPEG.absolute()),
        "-hide_banner",
        "-nostdin",
        "-y",
        "-nostats",
    )

    with tempfile.NamedTemporaryFile(
        suffix=f"{input_video_path.name}_stab.json"
    ) as tmpfile:
        stabilization_json_tmp_path = Path(tmpfile.name)
        cmds = (
            Command(
                name="stabilize",
                output=stabilized_video_path,
                commands=(
                    (
                        *ffmpeg_args,
                        "-i",
                        str(input_video_path.absolute()),
                        "-sws_flags",
                        "spline+accurate_rnd+full_chroma_int",
                        "-filter_complex",
                        f"tvai_cpe=model=cpe-2:filename='{stabilization_json_tmp_path.absolute()}':device=-2",
                        "-f",
                        "null",
                        "-",
                    ),
                    (
                        *ffmpeg_args,
                        "-i",
                        str(input_video_path.absolute()),
                        "-sws_flags",
                        "spline+accurate_rnd+full_chroma_int",
                        "-filter_complex",
                        ",".join(
                            (
                                f"tvai_stb=model=ref-2:filename='{stabilization_json_tmp_path.absolute()}':smoothness=12:rst=0:wst=0:cache=128:dof=1111:ws=32:full=0:roll=1:reduce=0:device=-2:vram=1:instances=1",
                                "fps=ntsc",
                                "scale=1920:-1",
                                f"lut3d=file='{lut_path.absolute()}'",
                                "normalize=smoothing=300:independence=0",
                            )
                        ),
                        "-c:v",
                        "hevc_videotoolbox",
                        "-profile:v",
                        "main",
                        "-tag:v",
                        "hvc1",
                        "-pix_fmt",
                        "yuv420p",
                        "-allow_sw",
                        "1",
                        "-g",
                        "30",
                        "-b:v",
                        "0",
                        "-q:v",
                        "50",
                        "-map",
                        "0:a?",
                        "-map_metadata:s:a:0",
                        "0:s:a:0",
                        "-c:a",
                        "copy",
                        "-map_metadata",
                        "0",
                        "-map_metadata:s:v",
                        "0:s:v",
                        "-movflags",
                        "frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr",
                        "-bf",
                        "0",
                        "-metadata",
                        "videoai=Stabilized auto-crop fixing rolling shutter and with smoothness 100",
                        str(stabilized_video_path),
                    ),
                ),
            ),
            Command(
                name="preview",
                output=preview_video_path,
                commands=(
                    (
                        *ffmpeg_args,
                        "-i",
                        str(input_video_path),
                        "-sws_flags",
                        "spline+accurate_rnd+full_chroma_int",
                        "-filter_complex",
                        ",".join(
                            (
                                "fps=ntsc",
                                "scale=1920:-1",
                                f"lut3d=file='{lut_path.absolute()}'",
                                "normalize=smoothing=300:independence=0",
                            )
                        ),
                        "-c:v",
                        "hevc_videotoolbox",
                        "-profile:v",
                        "main",
                        "-tag:v",
                        "hvc1",
                        "-pix_fmt",
                        "yuv420p",
                        "-allow_sw",
                        "1",
                        "-g",
                        "30",
                        "-b:v",
                        "0",
                        "-q:v",
                        "50",
                        "-map",
                        "0:a?",
                        "-map_metadata:s:a:0",
                        "0:s:a:0",
                        "-c:a",
                        "copy",
                        "-map_metadata",
                        "0",
                        "-map_metadata:s:v",
                        "0:s:v",
                        "-movflags",
                        "frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr",
                        "-bf",
                        "0",
                        str(preview_video_path),
                    ),
                ),
            ),
            Command(
                name="proxy",
                output=proxy_video_path,
                commands=(
                    (
                        *ffmpeg_args,
                        "-i",
                        str(input_video_path),
                        "-sws_flags",
                        "spline+accurate_rnd+full_chroma_int",
                        "-filter_complex",
                        ",".join(
                            (
                                "fps=ntsc",
                                "scale=1920:-1",
                            )
                        ),
                        "-c:v",
                        "hevc_videotoolbox",
                        "-profile:v",
                        "main",
                        "-tag:v",
                        "hvc1",
                        "-pix_fmt",
                        "yuv420p",
                        "-allow_sw",
                        "1",
                        "-g",
                        "30",
                        "-b:v",
                        "0",
                        "-q:v",
                        "50",
                        "-map",
                        "0:a?",
                        "-map_metadata:s:a:0",
                        "0:s:a:0",
                        "-c:a",
                        "copy",
                        "-map_metadata",
                        "0",
                        "-map_metadata:s:v",
                        "0:s:v",
                        "-movflags",
                        "frag_keyframe+empty_moov+delay_moov+use_metadata_tags+write_colr",
                        "-bf",
                        "0",
                        str(proxy_video_path),
                    ),
                ),
            ),
        )
        myenv = {**os.environ, **TOPAZ_ENV_VARS}
        for cmd_obj in cmds:
            if cmd_obj.output.exists() and cmd_obj.output.stat().st_size > 0:
                logging.info(
                    f"[{input_video_path}] Skipping {cmd_obj.name} as output exists: {cmd_obj.output}"
                )
                continue

            for i, cmd in enumerate(cmd_obj.commands):
                logging.info(
                    f"[{input_video_path}] Running {cmd_obj.name} step #{i + 1}"
                )
                cmd = [*cmd]

                if cmd[-1] == str(cmd_obj.output.absolute()):
                    tmp_output_path = cmd_obj.output.with_name(
                        f"{cmd_obj.output.stem}_tmp{cmd_obj.output.suffix}"
                    )
                    cmd[-1] = str(tmp_output_path.absolute())
                else:
                    tmp_output_path = None

                logging.debug(shlex.join(cmd))
                started_time_monotonic = time.monotonic()
                result = subprocess.run(
                    cmd,
                    cwd=FFMPEG.parent,
                    env={
                        **myenv,
                        "FFREPORT": f"file='{LOG_DIR}/{input_video_path.name}-{cmd_obj.name}.log':level={FFMPEG_LOG_LEVEL}",
                    },
                )
                elapsed_time = timedelta(
                    seconds=time.monotonic() - started_time_monotonic
                )
                if tmp_output_path:
                    logging.info(
                        f"[{input_video_path}] Moving {cmd_obj.output} to final location"
                    )
                    tmp_output_path.rename(cmd_obj.output)

                if not cmd_obj.output.exists():
                    logging.warn(
                        f"[{input_video_path}] Failed to create {cmd_obj.output} (ran for {elapsed_time})"
                    )
                if result.returncode != 0:
                    logging.warn(
                        f"[{input_video_path}] Failed to process - exited with {result.returncode} after {elapsed_time}"
                    )
                else:
                    logging.info(
                        f"[{input_video_path}] Done processing {cmd_obj.name} in {elapsed_time}"
                    )

    logging.info(f"[{input_video_path}] Done")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.info(f"Logging to {LOG_DIR}")

    log_file_path = LOG_DIR / "thumbnailer.log"
    file_handler = logging.FileHandler(log_file_path)
    log_format = logging.Formatter("%(asctime)s - %(name)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(log_format)

    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.DEBUG)  # Set the default log level
    logging.info(f"This program log will be at {log_file_path}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--lut", required=True, type=Path)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--input-video-glob", default="*.MP4")

    args = parser.parse_args()

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for path in args.files:
            if path.is_dir():
                paths = sorted(path.rglob(args.input_video_glob))
            else:
                paths = [path]
            futures: list[Future] = []
            logging.info(f"Found {len(paths)} files under {path}")
            for path in paths:
                if path.is_dir():
                    continue

                if "thumbnailer" in path.name or "_Proxy" in path.name:
                    continue

                try:
                    futures.append(
                        (
                            path,
                            executor.submit(
                                stabilize_and_apply_lut,
                                input_video_path=path,
                                lut_path=args.lut,
                            ),
                        )
                    )
                except Exception as e:
                    logging.exception(f"Failed on {path}: {e}")
                    # log exception info
                    continue

        for path, future in futures:
            try:
                future.result()
            except Exception as e:
                logging.exception(f"[{path}] Failed to process: {e}")
                continue


if __name__ == "__main__":
    raise SystemExit(main())
