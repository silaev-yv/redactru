from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Span:
    start: int
    end: int
    text: str
    type: str
    score: float
    meta: Dict

PRIORITY = {"SNILS":5, "PHONE":4, "PASSPORT":3, "ADDR":2, "PER":1}

def resolve_overlaps(spans: List[Span]) -> List[Span]:
    spans = sorted(spans, key=lambda s: (-PRIORITY.get(s.type,0), -s.score, s.start, -(s.end-s.start)))
    kept: List[Span] = []
    for s in spans:
        conflict = False
        for k in kept:
            if not (s.end <= k.start or s.start >= k.end):
                conflict = True
                break
        if not conflict:
            kept.append(s)
    return sorted(kept, key=lambda s: s.start)
