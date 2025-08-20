from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import stanza

@dataclass
class NerSpan:
    start: int
    end: int
    text: str
    label: str
    prob: float

class StanzaNER:
    def __init__(self, device: str = "cuda", use_gpu: bool = True):
        # Модели скачайте один раз: stanza.download('ru')
        self.nlp = stanza.Pipeline(
            lang="ru",
            processors="tokenize,ner",
            use_gpu=use_gpu,
            device=device
        )

    def find(self, text: str) -> List[NerSpan]:
        doc = self.nlp(text)
        out: List[NerSpan] = []
        for ent in doc.entities:
            # Типы: PER/ORG/LOC. Адресов нет — их берём regex/контекстом.
            out.append(NerSpan(
                start=ent.start_char,
                end=ent.end_char,
                text=text[ent.start_char:ent.end_char],
                label=ent.type,
                prob=getattr(ent, "score", 0.99)  # score есть не всегда
            ))
        return out
