import regex as re
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class RegexSpan:
    start: int
    end: int
    text: str
    rtype: str
    strength: float
    meta: Dict

# простые, но безопасные паттерны
RX_PHONE = re.compile(r'(?<!\d)(?:\+7|8)\s?[\s\-\(\)\d]{9,16}\d(?!\d)')
RX_SNILS = re.compile(r'(?<!\d)(\d{3}-\d{3}-\d{3}\s?\d{2})(?!\d)')
# адрес: мягкий каркас + маркеры, цифры дома и кв допускаются без точки
RX_ADDR = re.compile(
    r'((?:г\.?\s*\p{L}+|\p{L}+)?\s*'
    r'(?:(?:ул|просп|пр-кт|пер|пл|ш)\.?\s*[\p{L}\s\-\.]+,\s*)?'
    r'(?:д\.?\s*\d+[А-Яа-яA-Za-z]?)(?:,\s*(?:к|стр)\.?\s*\d+)?'
    r'(?:,\s*(?:кв)\.?\s*\d+)?'
    r'(?:[^\.]{0,60})?)',
    re.UNICODE
)

def find(text: str) -> List[RegexSpan]:
    spans: List[RegexSpan] = []
    for m in RX_PHONE.finditer(text):
        spans.append(RegexSpan(m.start(), m.end(), m.group(), "PHONE", 1.0, {}))
    for m in RX_SNILS.finditer(text):
        snils = m.group(1)
        if snils != "000-000-000 00":
            spans.append(RegexSpan(m.start(), m.end(), snils, "SNILS", 1.0, {}))
    # адрес как мягкий кандидат
    for m in RX_ADDR.finditer(text):
        spans.append(RegexSpan(m.start(), m.end(), m.group(1), "ADDR", 0.6, {}))
    return spans
