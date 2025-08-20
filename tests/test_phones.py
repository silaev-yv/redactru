from redactru.util.phones import iter_phone_spans, is_probable_ru_phone

def test_with_extension():
    s = "Контакт: +7 (999) 123-45-67 доб. 123."
    spans = list(iter_phone_spans(s))
    assert len(spans) == 1
    p = spans[0]
    assert p.digits == "79991234567"
    assert p.normalized == "+79991234567"
    assert p.has_ext and p.ext == "123"

def test_eight_prefix():
    s = "Позвонить: 8 999 123 45 67."
    p = list(iter_phone_spans(s))[0]
    assert p.normalized == "+79991234567"
    assert not p.has_ext

def test_compact():
    s = "Телефон: +79991234567."
    p = list(iter_phone_spans(s))[0]
    assert p.digits == "79991234567"
    assert p.normalized == "+79991234567"

def test_blocklist_contract_number():
    s = "Номер договора: 7-321-654-98-76 не является телефоном."
    assert list(iter_phone_spans(s)) == []

def test_probable_helper():
    assert is_probable_ru_phone("+7 (999) 123-45-67")
    assert is_probable_ru_phone("8 999 123 45 67")
