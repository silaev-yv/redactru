from dataclasses import dataclass
from typing import List, Dict, Optional
from .ner_stanza import StanzaNER
from . import regex_min
from .dictionaries import RUS_NAME_FIRST, STOP_UNITS, ADDR_MARKERS
from .normalizers import normalize_phone, snils_checksum_ok, addr_incomplete
from .resolver import resolve_overlaps, Span
from .profiles import WEIGHTS, THRESHOLDS

@dataclass
class Candidate:
    start: int; end: int; text: str; type: str
    ner_prob: float = 0.0
    regex_strength: float = 0.0
    dict_hit: int = 0
    ctx_feat: float = 0.0
    penalty: int = 0

class HybridAnonymizer:
    def __init__(self, device: str = "cuda"):
        self.ner = StanzaNER(device=device, use_gpu=True)

    def _context_score(self, text: str, start: int, end: int, t: str) -> float:
        left = text[max(0, start-24):start].lower()
        right = text[end:min(len(text), end+24)].lower()
        if t == "ADDR":
            return 1.0 if any(m in left+right for m in ADDR_MARKERS) else 0.0
        if t == "PER":
            token = text[start:end].strip().split()[0].lower().strip('.')
            return 1.0 if token in RUS_NAME_FIRST else 0.0
        return 0.0

    def _score(self, c: Candidate) -> float:
        w = WEIGHTS
        s = (w["ner"]*c.ner_prob + w["regex"]*c.regex_strength +
             w["dict"]*c.dict_hit + w["ctx"]*c.ctx_feat - w["penalty"]*c.penalty)
        return s

    def process(self, text: str, extra_regex_spans: Optional[List[Dict]] = None):
        cands: List[Candidate] = []

        # 1) NER → PER/ORG/LOC
        for s in self.ner.find(text):
            if s.label in {"PER", "LOC", "ORG"}:
                t = "PER" if s.label == "PER" else "LOC"
                cands.append(Candidate(s.start, s.end, s.text, t, ner_prob=s.prob))

        # 2) Regex: свои или fallback
        rx_spans = []
        if extra_regex_spans:
            rx_spans = extra_regex_spans
        else:
            rx_spans = [vars(x) for x in regex_min.find(text)]
        for r in rx_spans:
            cands.append(Candidate(r["start"], r["end"], r["text"], r["rtype"],
                                   regex_strength=r.get("strength", 1.0)))

        # 3) Фичи + скоринг
        spans: List[Span] = []
        for c in cands:
            # penalty для единиц/«макс.» рядом с кандидатами PER
            if c.type == "PER":
                token = c.text.lower().strip('.')
                if token in STOP_UNITS:
                    c.penalty = 1
            c.ctx_feat = self._context_score(text, c.start, c.end, c.type)
            sc = self._score(c)
            thr = THRESHOLDS.get(c.type, 0.7)
            if sc >= thr:
                m = {"score_parts": {"ner": c.ner_prob, "regex": c.regex_strength,
                                     "dict": c.dict_hit, "ctx": c.ctx_feat, "penalty": c.penalty}}
                # нормализация и спец-метки
                if c.type == "PHONE":
                    m["normalized"] = normalize_phone(c.text)
                if c.type == "SNILS":
                    m["checksum_ok"] = snils_checksum_ok(c.text)
                    if not m["checksum_ok"]:
                        continue
                if c.type == "ADDR":
                    m["addr_incomplete"] = addr_incomplete(c.text)
                spans.append(Span(c.start, c.end, c.text, c.type, sc, m))

        # 4) Снятие перекрытий
        spans = resolve_overlaps(spans)
        return spans
