from redactru.detect import detect_candidates

def test_detect_pack_basic():
    txt = (
        "СНИЛС: 112-233-445 95. "
        "Тел: +7 (999) 123-45-67. "
        "Республика Татарстан, г. Казань, пр-кт Победы, д 1."
    )
    cs = detect_candidates(txt)
    types = {c.typ for c in cs}
    assert "SNILS" in types
    assert "PHONE" in types
    assert "ADDR" in types
    # координаты возрастают
    starts = [c.start for c in cs]
    assert starts == sorted(starts)
