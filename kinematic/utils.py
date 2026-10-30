"""Performance and time management utilities."""

import time
from collections import deque
from typing import Any, List


class RingBuffer:
    """Fixed-capacity fast ring buffer for high-frequency tick storage."""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.buffer: deque = deque(maxlen=capacity)

    def append(self, item: Any):
        self.buffer.append(item)

    def get_all(self) -> List[Any]:
        return list(self.buffer)

    def __len__(self):
        return len(self.buffer)
