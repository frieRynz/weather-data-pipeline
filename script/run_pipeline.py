"""Single entrypoint: runs extract -> transform -> load in order.

Each stage runs as its own process (same behaviour as running the scripts
individually). The chain aborts immediately if any stage fails, so a broken
run never reaches the load stage with bad data.
"""
import subprocess
import sys
import time

from logger import setup_logger

logger = setup_logger("pipeline")

script_dir = __import__("os").path.dirname(__file__)
stages = [
    ("extract", "extract.py"),
    ("transform", "transform.py"),
    ("load", "load.py"),
]

start_time = time.time()
logger.info("========== Pipeline run started ==========")

for stage_name, stage_file in stages:
    logger.info(f"--- Stage: {stage_name} ---")
    result = subprocess.run([sys.executable, stage_file], cwd=script_dir)
    if result.returncode != 0:
        logger.error(f"Pipeline aborted: '{stage_name}' stage failed "
                     f"(exit code {result.returncode}). No further stages were run.")
        sys.exit(result.returncode)

duration = time.time() - start_time
logger.info(f"Pipeline run finished successfully in {round(duration, 2)} seconds")
print(f"Pipeline complete in {round(duration, 2)}s: extract -> transform -> load. "
      f"See logs/pipeline.log for details.")
