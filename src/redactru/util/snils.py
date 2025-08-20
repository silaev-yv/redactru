"""SNILS utilities: detection, normalization, checksum.

Алгоритм контрольной суммы:
- Суммируем цифры первых 9 позиций, умноженные на веса 9..1.
- Если сумма < 100 → КС = сумма.
- Если сумма в {100,101} → КС = 00.
- Иначе КС = сумма % 101; если результат в {100,101} → КС = 00.
Сравниваем с последними 2 цифрами.

Примеры (doctest):
>>> is_valid_snils("112-233-445 95")
True
>>> is_valid_snils("112-233-445 96")
False
>>> spans = list(iter_snils_spans("СНИЛС сотрудника: 11223344595."))
>>> len(spans), spans[0].digits, spans[0].is_valid
(1, '11223344595', True)
"""
from __future__ import annotations

import re
from typing import Iterator, NamedTuple

SNILS_RE = re.compile(r"(?<!\d)(\d{3})[-\s]?(\d{3})[-\s]?(\d{3})\s?(\d{2})(?!\d)")

class SnilsSpan(NamedTuple):
    start: int
    end: int
    raw: str
    digits: str
    normalized: str
    checksum: str
    is_valid: bool

def _checksum(d9: str) -> str:
    weights = range(9, 0, -1)
    s = sum(int(d) * w for d, w in zip(d9, weights))
    if s < 100:
        chk = s
    elif s in (100, 101):
        chk = 0
    else:
        chk = s % 101
        if chk in (100, 101):
            chk = 0
    return f"{chk:02d}"

def normalize_snils(text: str) -> str | None:
    """Вернуть нормализованную форму ###-###-### ## для первого вхождения или None."""
    m = SNILS_RE.search(text)
    if not m:
        return None
    g1, g2, g3, g4 = m.groups()
    return f"{g1}-{g2}-{g3} {g4}"

def is_valid_snils(snils: str) -> bool:
    """Проверка по формату и контрольной сумме. Дополнительно запрещаем 000-000-000 00."""
    digits = re.sub(r"\D", "", snils)
    if len(digits) != 11:
        return False
    d9, d2 = digits[:9], digits[9:]
    if d9 == "000000000":
        return False
    return _checksum(d9) == d2

def iter_snils_spans(text: str) -> Iterator[SnilsSpan]:
    """Итератор по всем SNILS-вхождениям в тексте."""
    for m in SNILS_RE.finditer(text):
        g1, g2, g3, g4 = m.groups()
        raw = text[m.start() : m.end()]
        digits = f"{g1}{g2}{g3}{g4}"
        normalized = f"{g1}-{g2}-{g3} {g4}"
        valid = is_valid_snils(digits)
        yield SnilsSpan(
            start=m.start(),
            end=m.end(),
            raw=raw,
            digits=digits,
            normalized=normalized,
            checksum=g4,
            is_valid=valid,
        )
