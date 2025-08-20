"""Утилиты работы со спанами (диапазонами) и заменами.

Определения:
- Спан — полуинтервал [start, end) в исходном тексте.
- Конфликты — пересечения спанов. Решаем по приоритету типов и длине.
- Применение — замены выполняются справа-налево, чтобы не сдвигать индексы.

Примеры (doctest):
>>> from redactru.util.spans import Span, resolve_overlaps, apply_spans
>>> txt = "Адрес: г. Казань, ул. Ленина, д 5. Тел: +7 (999) 123-45-67."
>>> spans = [
...   Span(start=7, end=33, typ="ADDR", text="г. Казань, ул. Ленина, д 5", replacement="[ADDR_001]"),
...   Span(start=41, end=64, typ="PHONE", text="+7 (999) 123-45-67", replacement="[PHONE_001]"),
... ]
>>> ok = resolve_overlaps(spans)
>>> new_text, ops = apply_spans(txt, ok)
>>> "[ADDR_001]" in new_text and "[PHONE_001]" in new_text
True
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple, Dict

# Приоритет типов по умолчанию
DEFAULT_PRIORITY: Tuple[str, ...] = ("SNILS", "PHONE", "ADDR", "PER")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    typ: str
    text: str
    replacement: str
    score: float | None = None  # опционально для будущего скоринга

    def normalized(self) -> "Span":
        """Гарантирует start<end и обрезку отрицательных индексов."""
        s = max(0, int(self.start))
        e = max(s, int(self.end))
        return Span(s, e, self.typ, self.text, self.replacement, self.score)

    @property
    def length(self) -> int:
        return max(0, self.end - self.start)


def _priority_index(typ: str, priority: Sequence[str]) -> int:
    try:
        return priority.index(typ.upper())
    except ValueError:
        # неизвестные типы считаем наименьшим приоритетом (в конец)
        return len(priority)


def _overlap(a: Span, b: Span) -> bool:
    return not (a.end <= b.start or b.end <= a.start)


def resolve_overlaps(
    spans: Iterable[Span],
    priority: Sequence[str] = DEFAULT_PRIORITY,
) -> List[Span]:
    """Убрать пересечения. Правила:
    1) Выше приоритет типа — выигрывает.
    2) При равенстве — длиннее спан выигрывает.
    3) При полном равенстве — первый по порядку.

    Возвращает непересекающиеся спаны, отсортированные по start.
    """
    items = [s.normalized() for s in spans if s.length > 0]
    items.sort(key=lambda s: (s.start, -s.length, _priority_index(s.typ, priority)))

    chosen: List[Span] = []
    for s in items:
        conflict_idx = None
        for i, c in enumerate(chosen):
            if _overlap(s, c):
                conflict_idx = i
                # Решить, кто важнее
                p_s = _priority_index(s.typ, priority)
                p_c = _priority_index(c.typ, priority)
                if p_s < p_c:
                    # s побеждает c
                    chosen[i] = s
                elif p_s == p_c:
                    # длиной
                    if s.length > c.length:
                        chosen[i] = s
                # если c выигрывает — ничего не делаем
                break
        else:
            chosen.append(s)

        # Если заменили конфликтный элемент, надо убедиться, что новый не пересекает других
        if conflict_idx is not None:
            # Перепройдём локально — набор маленький
            fixed: List[Span] = []
            for cand in chosen:
                if all(not _overlap(cand, x) for x in fixed):
                    fixed.append(cand)
                else:
                    # конфликт — выбираем по тем же правилам
                    for k, x in enumerate(fixed):
                        if _overlap(cand, x):
                            p_cand = _priority_index(cand.typ, priority)
                            p_x = _priority_index(x.typ, priority)
                            replace = (p_cand < p_x) or (p_cand == p_x and cand.length > x.length)
                            if replace:
                                fixed[k] = cand
                            break
            chosen = fixed

    chosen.sort(key=lambda s: s.start)
    return chosen


def apply_spans(text: str, spans: Iterable[Span]) -> Tuple[str, List[Dict[str, object]]]:
    """Применить замены к тексту. Возвращает (новый_текст, операции).

    Замены выполняются справа-налево, чтобы индексы не сдвигались.
    Каждая операция в отчёте: {start, end, typ, old, new}.
    """
    seq = [s.normalized() for s in spans if s.length > 0]
    seq.sort(key=lambda s: (s.start, s.end))  # слева-направо
    out = text
    ops: List[Dict[str, object]] = []

    for s in reversed(seq):
        before = out[: s.start]
        target = out[s.start : s.end]
        after = out[s.end :]
        out = before + s.replacement + after
        ops.append(
            {
                "start": s.start,
                "end": s.end,
                "typ": s.typ,
                "old": target,
                "new": s.replacement,
            }
        )

    ops.reverse()
    return out, ops
