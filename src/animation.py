class PageSlide:
    '''
    Slide of two canvas pages (sets of items sharing a tag) at constant speed:
    each step moves both pages by a fixed amount, like the original app.
    The incoming page is expected to be drawn offset by +distance on x;
    over the animation both pages move by -distance in total.
    Starting a new slide while one is running finishes the running one first,
    so at most two pages exist at any time.
    '''

    def __init__(self, move, delete, step=20):
        self._move = move
        self._delete = delete
        self._step = step
        self._active = False

    @property
    def active(self):
        return self._active

    def start(self, outgoing, incoming, distance):
        self.finish()
        self._outgoing = outgoing
        self._incoming = incoming
        self._distance = distance
        self._applied = 0.0
        self._active = True

    def step(self):
        '''Advance one tick. Return True while the slide is still running.'''
        if not self._active:
            return False
        remaining = abs(self._distance) - abs(self._applied)
        if remaining <= self._step:
            self.finish()
            return False
        direction = -1 if self._distance > 0 else 1
        self._move_by(direction * self._step)
        return True

    def finish(self):
        if not self._active:
            return
        self._move_by(-self._distance - self._applied)
        self._delete(self._outgoing)
        self._active = False

    def _move_by(self, dx):
        self._move(self._outgoing, dx)
        self._move(self._incoming, dx)
        self._applied += dx
