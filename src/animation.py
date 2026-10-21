def ease_out_cubic(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


class PageSlide:
    '''
    Time-based slide of two canvas pages (sets of items sharing a tag).
    The incoming page is expected to be drawn offset by +distance on x;
    over the animation both pages move by -distance in total.
    Starting a new slide while one is running finishes the running one first,
    so at most two pages exist at any time.
    '''

    def __init__(self, move, delete, duration=0.18):
        self._move = move
        self._delete = delete
        self._duration = duration
        self._active = False

    @property
    def active(self):
        return self._active

    def start(self, outgoing, incoming, distance, now):
        self.finish()
        self._outgoing = outgoing
        self._incoming = incoming
        self._distance = distance
        self._started_at = now
        self._applied = 0.0
        self._active = True

    def step(self, now):
        if not self._active:
            return False
        elapsed = now - self._started_at
        # small tolerance so float rounding of timestamps doesn't add a frame
        if elapsed >= self._duration - 1e-9:
            self.finish()
            return False
        self._move_to(-self._distance * ease_out_cubic(elapsed / self._duration))
        return True

    def finish(self):
        if not self._active:
            return
        self._move_to(-self._distance)
        self._delete(self._outgoing)
        self._active = False

    def _move_to(self, target):
        dx = target - self._applied
        self._move(self._outgoing, dx)
        self._move(self._incoming, dx)
        self._applied = target
