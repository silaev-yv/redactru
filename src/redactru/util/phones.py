"""Russian phone detection and normalization.

Поддерживаем:
- +7XXXXXXXXXX, 8XXXXXXXXXX, 7XXXXXXXXXX
- +7 (XXX) XXX-XX-XX, 8 XXX XXX XX XX, вариативные пробелы/дефисы/скобки
- добавочный: "доб.", "ext." + 1..6 цифр
- отсекаем ложные срабатывания по левому контексту (напр. "СНИЛС", "договор")

Нормализация: E.164 ➜ "+7" + 10 цифр. Префикс "8" приводим к "+7". Без префикса — считаем Россией и делаем "+7" + 10 цифр.

Примеры (doctest):
>>> is_probable_ru_phone("+7 (999) 123-45-67")
True
>>> spans = list(iter_phone_spans("Контакт: +7 (999) 123-45-67 доб. 123."))
>>> len(spans), spans[0].digits, spans[0].normalized, spans[0].ext, spans[0].has_ext
(1, '79991234567', '+79991234567', '123', True)
>>> spans = list(iter_phone_spans("Позвонить: 8 999 123 45 67."))
>>> len(spans), spans[0].digits, spans[0].normalized, spans[0].has_ext
(1, '89991234567', '+79991234567', False)
>>> list(iter_phone_spans("Номер договора: 7-321-654-98-76 не является телефоном."))
[]
"""
from __future__ import annotations

import re
from typing import Iterator, NamedTuple, Optional

# Основной шаблон: компактный вариант или вариант с маской и/или скобками
PHONE_RE = re.compile(
    r"""
    (?<!\d)
    (?:
        (?P<compact>(?:\+7|8|7)\d{10})
      |
        (?:(?P<prefix>\+7|8|7)\s*[- ]*)?
        (?:\(\s*(?P<area>\d{3})\s*\)|(?P<area2>\d{3}))
        \s*[- ]*(?P<d1>\d{3})\s*[- ]*(?P<d2>\d{2})\s*[- ]*(?P<d3>\d{2})
    )
    (?:\s*(?:доб\.?|ext\.?)\s*(?P<ext>\d{1,6}))?
    (?!\d)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Слова в левом контексте, при которых совпадение игнорируем
#LEFT_CONTEXT_BLOCKLIST = (
#    "снилс", "snils", "договор", "контракт", "акт ", "накладн", "инн", "паспорт"
#)

#LEFT_LABELS = ("снилс", "snils", "инн", "паспорт", "договор", "контракт", "акт", "накладн")
LABEL_PREFIXES = ("снилс", "snils", "инн", "паспорт", "договор", "контракт", "акт", "наклад")

class PhoneSpan(NamedTuple):
    start: int
    end: int
    raw: str
    digits: str          # только цифры, 11 для РФ-паттерна
    normalized: str      # "+7XXXXXXXXXX"
    ext: Optional[str]   # добавочный, если есть
    has_ext: bool

def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s)

def _normalize(digits: str) -> Optional[str]:
    """Вернёт '+7XXXXXXXXXX' или None, если число не похоже на RU."""
    if len(digits) == 11 and digits[0] in ("7", "8"):
        core = digits[1:]
        return "+7" + core
    if len(digits) == 10:
        return "+7" + digits
    return None

def is_probable_ru_phone(text: str) -> bool:
    """Грубая проверка по цифрам и префиксу."""
    d = _only_digits(text)
    if len(d) == 11 and d[0] in ("7", "8"):
        return True
    if len(d) == 10:
        return True
    return False

def _blocked_by_left_context(full_text: str, start: int) -> bool:
    left = full_text[max(0, start - 48): start]
    m = re.search(r"([A-Za-zА-Яа-яЁё\.]{1,24})\s*[:№#]?\s*$", left)
    if not m:
        return False
    label = m.group(1).lower().strip().rstrip(".")
    return any(label.startswith(pfx) for pfx in LABEL_PREFIXES)

def iter_phone_spans(text: str) -> Iterator[PhoneSpan]:
    """Итератор по телефонным вхождениям с нормализацией к E.164 (+7...)."""
    for m in PHONE_RE.finditer(text):
        if _blocked_by_left_context(text, m.start()):
            continue

        raw = text[m.start(): m.end()].strip()
        ext = m.group("ext")
        compact = m.group("compact")

        if compact:
            digits = _only_digits(compact)
        else:
            prefix = m.group("prefix") or ""
            area = m.group("area") or m.group("area2") or ""
            d1, d2, d3 = m.group("d1"), m.group("d2"), m.group("d3")
            digits = _only_digits(prefix + area + d1 + d2 + d3)

        normalized = _normalize(digits)
        if not normalized:
            continue

        yield PhoneSpan(
            start=m.start(),
            end=m.end(),
            raw=raw,
            digits=digits,
            normalized=normalized,
            ext=ext if ext else None,
            has_ext=bool(ext),
        )
