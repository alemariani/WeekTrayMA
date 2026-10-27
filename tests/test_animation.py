import pytest

from animation import PageSlide


class FakeCanvas:
    def __init__(self):
        self.moves, self.deleted = {}, []

    def move(self, tag, dx):
        self.moves[tag] = self.moves.get(tag, 0.0) + dx

    def delete(self, tag):
        self.deleted.append(tag)


def make(step=20):
    c = FakeCanvas()
    return c, PageSlide(c.move, c.delete, step=step)


def run_to_end(slide):
    ticks = 0
    while slide.step():
        ticks += 1
    return ticks + 1


def test_each_tick_moves_both_pages_by_the_step():
    c, s = make()
    s.start("p0", "p1", 300.0)
    assert s.step() is True
    assert c.moves == {"p0": -20.0, "p1": -20.0}


def test_full_slide_takes_distance_over_step_ticks():
    c, s = make()
    s.start("p0", "p1", 300.0)
    assert run_to_end(s) == 15
    assert c.moves["p0"] == pytest.approx(-300.0)
    assert c.moves["p1"] == pytest.approx(-300.0)
    assert c.deleted == ["p0"] and not s.active


def test_last_tick_moves_only_the_remainder():
    c, s = make()
    s.start("p0", "p1", 50.0)
    assert run_to_end(s) == 3
    assert c.moves["p1"] == pytest.approx(-50.0)


def test_negative_distance_slides_the_other_way():
    c, s = make()
    s.start("p0", "p1", -300.0)
    s.step()
    assert c.moves["p1"] == 20.0
    run_to_end(s)
    assert c.moves["p1"] == pytest.approx(300.0)


def test_restart_while_active_snaps_previous_then_starts_new():
    c, s = make()
    s.start("p0", "p1", 300.0)
    s.step()
    s.start("p1", "p2", -300.0)
    assert c.deleted == ["p0"]
    assert c.moves["p1"] == pytest.approx(-300.0)
    run_to_end(s)
    assert c.deleted == ["p0", "p1"]
    assert c.moves["p2"] == pytest.approx(300.0)


def test_many_rapid_restarts_leave_only_last_page():
    c, s = make()
    tags = [f"p{i}" for i in range(10)]
    for i in range(9):
        s.start(tags[i], tags[i + 1], 300.0)
        s.step()
    s.finish()
    assert c.deleted == tags[:9]
    assert not s.active


def test_finish_when_inactive_is_noop():
    c, s = make()
    s.finish()
    assert c.moves == {} and c.deleted == []
