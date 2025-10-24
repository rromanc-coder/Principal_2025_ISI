import time
from collections import defaultdict, deque

HISTORY_WINDOW = 60  # muestras en memoria (cada /status)
# name -> deque[{ts, up, lat, err}]
history = defaultdict(lambda: deque(maxlen=HISTORY_WINDOW))
last_error = {}  # name -> str

def now_ts() -> float:
    return time.time()
