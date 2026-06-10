import os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "data", "applications.json")
MEMORY_ROOT = os.path.join(BASE, "memory")
LOG_DIR = os.path.join(BASE, "logs")
EVAL_DIR = os.path.join(BASE, "evaluator", "runs")
DASHBOARD_FILE = os.path.join(BASE, "dashboard", "board_dashboard.html")

# starting architecture config -- intentionally conservative so the optimizer has room
INITIAL_CONFIG = {
    "parallelism": 1,     # start sequential -- intentionally leaves headroom to optimize
    "max_retries": 0,     # the evaluator may turn this on
}
