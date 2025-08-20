from types import SimpleNamespace
import pytest

import hybrid.aggregator as agg
from hybrid.aggregator import HybridAnonymizer


class DummyNER:
    def __init__(self, spans):
        self._spans = spans

    def find(self, text):
        return self._spans


def test_addr_tail(monkeypatch):
    monkeypatch.setattr(agg, "StanzaNER", lambda *a, **k: DummyNER([]))
    t = "г. Томск, пер. Чехова, д.7, кв. 14."
    addr = "пер. Чехова, д.7, кв. 14"
    start = t.index(addr)
    spans = HybridAnonymizer(device="cpu").process(
        t,
        extra_regex_spans=[{"start": start, "end": start + len(addr), "text": addr, "rtype": "ADDR", "strength": 1.01}],
    )
    assert any(s.type == "ADDR" and "кв. 14" in s.text for s in spans)


def test_max_not_per(monkeypatch):
    t = "Макс. скорость 60 км/ч. Коллега Макс Иванов пришёл."
    spans_ner = [
        SimpleNamespace(start=t.index("Макс."), end=t.index("Макс.") + 5, text="Макс.", label="PER", prob=1.0),
        SimpleNamespace(
            start=t.index("Макс Иванов"),
            end=t.index("Макс Иванов") + len("Макс Иванов"),
            text="Макс Иванов",
            label="PER",
            prob=2.0,
        ),
    ]
    monkeypatch.setattr(agg, "StanzaNER", lambda *a, **k: DummyNER(spans_ner))
    spans = HybridAnonymizer(device="cpu").process(t)
    assert any(s.type == "PER" and "Макс Иванов" in s.text for s in spans)
    assert not any(s.type == "PER" and s.text == "Макс." for s in spans)


def test_dict_hit_per(monkeypatch):
    t = "Иван пришёл."
    spans_ner = [
        SimpleNamespace(start=t.index("Иван"), end=t.index("Иван") + len("Иван"), text="Иван", label="PER", prob=1.0)
    ]
    monkeypatch.setattr(agg, "StanzaNER", lambda *a, **k: DummyNER(spans_ner))
    spans = HybridAnonymizer(device="cpu").process(t)
    assert any(s.type == "PER" and s.text == "Иван" for s in spans)

