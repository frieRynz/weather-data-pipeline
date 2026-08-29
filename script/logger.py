import logging
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.abspath(os.path.join(script_dir, "..", "logs"))
os.makedirs(log_dir, exist_ok=True)


def setup_logger(name):
    """Return a named logger writing to the shared pipeline.log.

    basicConfig only configures the root logger once per process; calling it
    from every script is fine because the first call wins and all subsequent
    runs share the same file/format.
    """
    logging.basicConfig(
        filename=os.path.join(log_dir, "pipeline.log"),
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(name)