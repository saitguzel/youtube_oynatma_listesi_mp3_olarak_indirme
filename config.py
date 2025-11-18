import os

# Output folder (will be created if missing)
OUTPUT_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Default parallel worker count
DEFAULT_MAX_WORKERS = 3

# Maximum retry count for a single video download
MAX_RETRIES = 3

# If True, print extra debug/log lines to console
VERBOSE_LOGGING = True
