"""Поиск кандидатов: SNILS, PHONE, ADDR, PER. Грубый гибрид (regex + эвристики).

Примеры (doctest):
>>> from redactru.detect import detect_candidates
>>> txt = "СНИЛС: 112-233-445 95. Тел: +7 (999) 123-45-67. Республика Татарстан, г. Казань, пр-кт Победы, д 1."
>>> types = sorted({c.typ for c in detect_candidates(txt)})
>>> ("SNILS" in types) and ("PHONE" in types) and ("ADDR" in types)
True
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List
import re

from redactru.util.snils import iter_snils_spans
from redactru.util.phones import iter_phone_spans
from redactru.rules.regex_ru import iter_address_spans, iter_person_spans
from redactru.util.spans import Span, resolve_overlaps, DEFAULT_PRIORITY


@dataclass(frozen=True)
class Candidate:
    id: str
    typ: str           # SNILS | PHONE | ADDR | PER
    start: int
    end: int
    text: str
    norm: str | None   # нормализованная форма, если есть
    score: float       # 0..1
    meta: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _snils_candidates(text: str) -> Iterable[Span]:
    for s in iter_snils_spans(text):
        score = 1.0 if s.is_valid else 0.2
        yield Span(start=s.start, end=s.end, typ="SNILS", text=text[s.start:s.end],
                   replacement="[SNILS]", score=score)


def _phone_candidates(text: str) -> Iterable[Span]:
    for p in iter_phone_spans(text):
        yield Span(start=p.start, end=p.end, typ="PHONE", text=text[p.start:p.end],
                   replacement="[PHONE]", score=0.9)


# Робастный фоллбэк для коротких адресных фраз в одном предложении
USE_FALLBACK_ADDR = False
_FALLBACK_ADDR_RE = re.compile(
    r"""(?P<addr>
        (?:г\.?|город)\s+[^\n\r.!?]{1,120}?                # город + контекст
        (?:ул\.?|улица|пр-?кт|проспект|пер\.?|переулок)    # улица/проспект/пер.
        [^\n\r.!?]{0,120}?
        (?:д\.?|дом)\s*\d+[^\n\r.!?]*                      # дом N и хвост
    )""",
    re.IGNORECASE | re.VERBOSE,
)

def _addr_candidates(text: str) -> Iterable[Span]:
    for a in iter_address_spans(text):
        yield Span(start=a.start, end=a.end, typ="ADDR", text=a.raw, replacement="[ADDR]", score=0.7)
    if USE_FALLBACK_ADDR:
        for m in _FALLBACK_ADDR_RE.finditer(text):
            yield Span(start=m.start("addr"), end=m.end("addr"), typ="ADDR",
                       text=m.group("addr"), replacement="[ADDR]", score=0.6)


def _per_candidates(text: str) -> Iterable[Span]:
    for per in iter_person_spans(text):
        yield Span(start=per.start, end=per.end, typ="PER", text=per.raw,
                   replacement="[PER]", score=0.5)


def _make_candidate(span: Span, text: str) -> Candidate:
    if span.typ == "SNILS":
        from redactru.util.snils import normalize_snils, is_valid_snils
        norm = normalize_snils(span.text)
        meta = {"valid": bool(norm and is_valid_snils(norm))}
    elif span.typ == "PHONE":
        from redactru.util.phones import _only_digits as only_digits, _normalize as norm_phone
        digits = only_digits(span.text)
        norm = norm_phone(digits)
        meta = {"digits": digits}
    elif span.typ == "ADDR":
        norm = None
        meta = {}
    else:  # PER
        norm = None
        meta = {"kind": "regex"}
    return Candidate(
        id=f"{span.typ}:{span.start}-{span.end}",
        typ=span.typ,
        start=span.start,
        end=span.end,
        text=span.text,
        norm=norm,
        score=float(span.score or 0.0),
        meta=meta,
    )


def detect_candidates(text: str, priority: Iterable[str] = DEFAULT_PRIORITY) -> List[Candidate]:
    spans: List[Span] = []
    spans.extend(_snils_candidates(text))
    spans.extend(_phone_candidates(text))
    spans.extend(_addr_candidates(text))
    spans.extend(_per_candidates(text))

    resolved = resolve_overlaps(spans, list(priority))
    out = [_make_candidate(s, text) for s in resolved]
    out.sort(key=lambda c: c.start)
    return out


def detect_file(path: str, encoding: str = "utf-8") -> List[Candidate]:
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        txt = f.read()
    return detect_candidates(txt)
