"""Русские регэкспы и простые эвристики для кандидатов PER и адресных маркеров.

Примеры (doctest):
>>> from redactru.rules.regex_ru import iter_person_spans, has_address_markers, iter_address_markers
>>> txt = "Выступал Иванов И.И., затем Анна-Мария де Ла Крус и Пётр Сидоров."
>>> spans = [s.raw for s in iter_person_spans(txt)]
>>> any("Иванов И.И." in r for r in spans)
True
>>> has_address_markers("г. Казань, пр-кт Победы, д 1, кв. 3")
True
>>> [t.token for t in iter_address_markers("Республика Татарстан, г. Казань, ул. Ленина, д. 5")]
['Республика', 'г.', 'ул.', 'д.']
"""
from __future__ import annotations
import re
from typing import Iterator, NamedTuple

try:
    from redactru.nlp.morph import is_person_like as _is_person_like
except Exception:
    def _is_person_like(_t: str) -> bool:
        return True  # если морфология недоступна, не фильтруем
    
try:
    from redactru.nlp.morph import is_name_token as _is_name, is_surname_token as _is_surname
except Exception:
    _is_name = lambda _t: True
    _is_surname = lambda _t: True

_LEFT_STOP = {"когда", "если", "где", "как", "что", "почему", "зачем"}
def _bad_left_context(text: str, start: int) -> bool:
    left = text[max(0, start-24): start]
    m = re.search(r"([A-Za-zА-Яа-яЁё]+)\s*$", left)
    return bool(m and m.group(1).lower() in _LEFT_STOP)

# ===== PERSON (ФИО) =====

_PARTICLES = r"(?:де|дель|фон|ван|аль)"
_CAP = r"[А-ЯЁ][а-яё]+"
_HYPHEN_CAP = rf"{_CAP}(?:-{_CAP})*"
_SURNAME = rf"(?:{_HYPHEN_CAP}|{_PARTICLES}\s+{_CAP})"
_NAME = _CAP
_INITIALS = r"[А-ЯЁ]\.\s*[А-ЯЁ]\."

RE_SURNAME_INITIALS = re.compile(rf"(?<!\w)(?P<surname>{_SURNAME})\s+(?P<init>{_INITIALS})(?!\w)")
RE_INITIALS_SURNAME = re.compile(rf"(?<!\w)(?P<init>{_INITIALS})\s+(?P<surname>{_SURNAME})(?!\w)")
RE_NAME_SURNAME = re.compile(rf"(?<!\w)(?P<name>{_NAME})\s+(?P<surname>{_SURNAME})(?!\w)")
_PATR = r"(?:[А-ЯЁ][а-яё]+(?:ович|евич|ич|овна|евна|ична))"
RE_SURNAME_NAME_OPT_PATR = re.compile(
    rf"(?<!\w)(?P<surname>{_SURNAME})\s+(?P<name>{_NAME})(?:\s+(?P<patr>{_PATR}))?(?!\w)"
)

ALLOW_SINGLE_NAME = False  # включи True, если нужны одиночные имена
_COMMON_SHORT_NAMES = {"Макс","Саша","Женя","Паша","Лена","Дима","Маша","Оля","Игорь","Ира","Лёша","Леша"}
SINGLE_NAME_RE = re.compile(r"(?<!\w)([А-ЯЁ][а-яё]{2,})(?!\w)")

class PersonSpan(NamedTuple):
    start: int
    end: int
    raw: str
    kind: str  # 'SN+I', 'I+SN', 'N+SN', 'SN+N(+P)'

def _yield_person(m: re.Match, kind: str, text: str) -> PersonSpan:
    return PersonSpan(start=m.start(), end=m.end(), raw=text[m.start():m.end()], kind=kind)

def iter_person_spans(text: str) -> Iterator[PersonSpan]:
    for m in RE_SURNAME_INITIALS.finditer(text):
        sn = m.group("surname")
        if _is_surname(sn) and not _bad_left_context(text, m.start()):
            yield _yield_person(m, "SN+I", text)

    for m in RE_INITIALS_SURNAME.finditer(text):
        sn = m.group("surname")
        if _is_surname(sn) and not _bad_left_context(text, m.start()):
            yield _yield_person(m, "I+SN", text)

    for m in RE_NAME_SURNAME.finditer(text):
        nm, sn = m.group("name"), m.group("surname")
        if _is_name(nm) and _is_surname(sn) and not _bad_left_context(text, m.start()):
            yield _yield_person(m, "N+SN", text)

    for m in RE_SURNAME_NAME_OPT_PATR.finditer(text):
        sn, nm = m.group("surname"), m.group("name")
        if _is_surname(sn) and _is_name(nm) and not _bad_left_context(text, m.start()):
            yield _yield_person(m, "SN+N(+P)", text)
    
    if ALLOW_SINGLE_NAME:
        for m in SINGLE_NAME_RE.finditer(text):
            tok = m.group(1)
            if _bad_left_context(text, m.start()):
                continue
            if _is_name(tok) or tok in _COMMON_SHORT_NAMES:
                yield _yield_person(m, "N", text)

PER_STOPWORDS = {
    "макс", "макс.", "мин", "мин.", "мм", "см", "м", "сек", "сек.", "кпа", "°c",
    "инн", "снилс", "паспорт", "дог.", "договор"
}
def likely_not_person(token: str) -> bool:
    return token.strip().lower() in PER_STOPWORDS

# ===== ADDRESS MARKERS =====
_ADDRESS_TOKENS = (
    r"г\.", r"город", r"обл\.?", r"область", r"респ\.?", r"республика", r"край",
    r"р-?н", r"район", r"пос\.?", r"посёлок", r"пгт",
    r"с\.", r"село",
    r"ул\.?", r"улица", r"пр-?кт", r"проспект", r"пер\.?", r"переулок",
    r"б-?р", r"бульвар", r"бул\.?", r"ш\.?", r"шоссе",
    r"д\.", r"дом", r"к\.", r"корп\.?", r"корпус", r"стр\.?", r"строение", r"кв\.?", r"квартира"
)
ADDRESS_MARKER_RE = re.compile(rf"(?<!\w)(?:{'|'.join(_ADDRESS_TOKENS)})(?!\w)", re.IGNORECASE)

# Ограничители адресного куска
_MAX_ADDR_LEN = 160

def _accept_address(chunk: str) -> bool:
    if len(chunk) > _MAX_ADDR_LEN:
        return False
    if chunk.count("\n") > 1:
        return False
    city_markers = len(re.findall(r"(?<!\w)(?:г\.|город)(?!\w)", chunk, flags=re.IGNORECASE))
    if city_markers >= 2:
        return False
    if "»," in chunk or "», то" in chunk.lower():
        return False
    return True

# Грубый span: ≥2 маркера + дом + опциональные к/стр/кв хвосты
ADDRESS_SPAN_RE = re.compile(
    rf"""
    (?P<chunk>
        (?:(?<!\w)(?:{'|'.join(_ADDRESS_TOKENS)})(?!\w).+?)
        (?:(?<!\w)(?:{'|'.join(_ADDRESS_TOKENS)})(?!\w).+?)
        (?:\b(?:д\.?|дом)\s*\d+[A-Za-zА-Яа-я0-9/-]*)
        (?:\s*[,;]?\s*(?:к\.?|корп\.?|корпус|стр\.?|строение|кв\.?|квартира)\s*[A-Za-zА-Яа-я0-9/-]+)*
    )
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)
# если основное совпадение закончилось ровно на метке (к/стр/кв), дотянем число справа
_TAIL_AFTER_LABEL_RE = re.compile(r"\.?\s*\d+[A-Za-zА-Яа-я0-9/-]*")
_LABEL_END_RE = re.compile(r"(кв\.?|к\.|корп\.?|корпус|стр\.?|строение)\s*$", re.IGNORECASE)

class AddressMarker(NamedTuple):
    start: int
    end: int
    token: str

def has_address_markers(text: str) -> bool:
    return ADDRESS_MARKER_RE.search(text) is not None

def iter_address_markers(text: str) -> Iterator[AddressMarker]:
    for m in ADDRESS_MARKER_RE.finditer(text):
        yield AddressMarker(start=m.start(), end=m.end(), token=m.group(0))

class AddressSpan(NamedTuple):
    start: int
    end: int
    raw: str

def iter_address_spans(text: str) -> Iterator[AddressSpan]:
    for m in ADDRESS_SPAN_RE.finditer(text):
        s, e = m.start(), m.end()
        raw = text[s:e]

        # если матч оборвался на метке — дотянуть число
        if _LABEL_END_RE.search(raw):
            m2 = _TAIL_AFTER_LABEL_RE.match(text, e)
            if m2:
                e = m2.end()
                raw = text[s:e]

        if _accept_address(raw):
            yield AddressSpan(start=s, end=e, raw=raw)

