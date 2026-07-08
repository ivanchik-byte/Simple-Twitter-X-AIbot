import functools
import yaml
import logging

logger = logging.getLogger(__name__)
CONFIG_PATH = "config.yaml"

@functools.lru_cache(maxsize=1)
def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading {CONFIG_PATH}: {e}")
        return {}
