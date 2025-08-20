from redactru.util.spans import Span, resolve_overlaps, apply_spans, DEFAULT_PRIORITY

def test_apply_basic():
    txt = "Адрес: г. Казань, ул. Ленина, д 5. Тел: +7 (999) 123-45-67."
    spans = [
        Span(start=7, end=33, typ="ADDR", text="г. Казань, ул. Ленина, д 5", replacement="[ADDR_001]"),
        Span(start=41, end=64, typ="PHONE", text="+7 (999) 123-45-67", replacement="[PHONE_001]"),
    ]
    ok = resolve_overlaps(spans, DEFAULT_PRIORITY)
    out, ops = apply_spans(txt, ok)
    assert "[ADDR_001]" in out and "[PHONE_001]" in out
    assert ops[0]["typ"] == "ADDR" and ops[1]["typ"] == "PHONE"

def test_overlap_priority():
    # PHONE пересекается с PER, должен победить PHONE по приоритету
    a = Span(10, 25, "PER", "Иванов И.И.", "[PER_001]")
    b = Span(12, 28, "PHONE", "+7 (999) 123-45-67", "[PHONE_001]")
    chosen = resolve_overlaps([a, b], DEFAULT_PRIORITY)
    assert len(chosen) == 1 and chosen[0].typ == "PHONE"

def test_overlap_length_when_same_type():
    # Один и тот же тип: выигрывает более длинный спан
    a = Span(5, 10, "ADDR", "ул. Лени", "[ADDR_001]")
    b = Span(5, 15, "ADDR", "ул. Ленина", "[ADDR_002]")
    chosen = resolve_overlaps([a, b], DEFAULT_PRIORITY)
    assert len(chosen) == 1 and chosen[0].replacement == "[ADDR_002]"

def test_apply_keeps_indices_order():
    txt = "ABCDEF"
    spans = [Span(1, 3, "PER", "BC", "[X]"), Span(3, 5, "PER", "DE", "[Y]")]
    out, _ = apply_spans(txt, resolve_overlaps(spans))
    assert out == "A[X][Y]F"
