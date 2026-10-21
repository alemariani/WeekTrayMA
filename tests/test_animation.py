import pytest

from animation import PageSlide, ease_out_cubic


class FakeCanvas:
    def __init__(self):
        self.moves, self.deleted = {}, []

    def move(self, tag, dx):
        self.moves[tag] = self.moves.get(tag, 0.0) + dx

    def delete(self, tag):
        self.deleted.append(tag)


def make():
    c = FakeCanvas()
    return c, PageSlide(c.move, c.delete, duration=0.18)


def test_ease_out_cubic_bounds_and_clamp():
    assert ease_out_cubic(0) == 0 and ease_out_cubic(1) == 1
    assert ease_out_cubic(-1) == 0 and ease_out_cubic(2) == 1
    assert ease_out_cubic(0.5) > 0.5


def test_full_run_moves_exact_distance_and_deletes_outgoing():
    c, s = make()
    s.start("p0", "p1", 300.0, now=10.0)
    assert s.step(10.05) is True
    assert s.step(10.18) is False
    assert c.moves["p0"] == pytest.approx(-300.0)
    assert c.moves["p1"] == pytest.approx(-300.0)
    assert c.deleted == ["p0"] and not s.active


def test_first_step_moves_immediately():
    c, s = make()
    s.start("p0", "p1", 300.0, now=0.0)
    s.step(0.016)
    assert c.moves["p1"] < -10


def test_restart_while_active_snaps_previous_then_starts_new():
    c, s = make()
    s.start("p0", "p1", 300.0, now=0.0)
    s.step(0.05)
    s.start("p1", "p2", -300.0, now=0.06)
    assert c.deleted == ["p0"]
    assert c.moves["p1"] == pytest.approx(-300.0)
    s.step(1.0)
    assert c.deleted == ["p0", "p1"]
    assert c.moves["p2"] == pytest.approx(300.0)


def test_many_rapid_restarts_leave_only_last_page():
    c, s = make()
    tags = [f"p{i}" for i in range(10)]
    for i in range(9):
        s.start(tags[i], tags[i + 1], 300.0, now=i * 0.01)
        s.step(i * 0.01 + 0.005)
    s.finish()
    assert c.deleted == tags[:9]
    assert not s.active


def test_finish_when_inactive_is_noop():
    c, s = make()
    s.finish()
    assert c.moves == {} and c.deleted == []
