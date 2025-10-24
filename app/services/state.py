import time
from collections import defaultdict, deque

HISTORY_WINDOW = 60  # muestras en memoria (cada /status)
history = defaultdict(lambda: deque(maxlen=HISTORY_WINDOW))  # name -> deque[{ts, up, lat, err}]
last_error = {}  # name -> str

def now_ts() -> float:
    return time.time()
