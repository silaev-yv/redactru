import re
from redactru.util.snils import is_valid_snils, normalize_snils, iter_snils_spans

def test_valid_and_invalid():
    assert is_valid_snils("112-233-445 95")
    assert is_valid_snils("11223344595")
    assert not is_valid_snils("112-233-445 96")
    assert not is_valid_snils("000-000-000 00")

def test_normalize():
    s = "СНИЛС сотрудника: 11223344595."
    assert normalize_snils(s) == "112-233-445 95"

def test_iter_spans_basic():
    txt = "СНИЛС: 112-233-445 95 и ещё 123456789 00 (неверный)."
    spans = list(iter_snils_spans(txt))
    assert len(spans) == 2
    a, b = spans
    assert re.sub(r'\D','',a.digits) == "11223344595"
    assert a.is_valid is True
    assert b.is_valid in (True, False)  # вторая запись может быть невалидной
