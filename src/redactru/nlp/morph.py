"""Морфология: pymorphy3 + Petrovich (устойчиво к разным версиям petrovich)."""
from __future__ import annotations
from typing import Optional
import pymorphy3

_morph = pymorphy3.MorphAnalyzer()

# --- petrovich (опционально) ---
try:
    from petrovich.main import Petrovich
    from petrovich.enums import Case, Gender
    _PETROVICH_AVAILABLE = True
    _pv = Petrovich()
except Exception:  # petrovich не установлен или иная версия
    _PETROVICH_AVAILABLE = False
    Case = None  # type: ignore
    Gender = None  # type: ignore
    _pv = None  # type: ignore

# OpenCorpora -> строковые значения кейсов Petrovich
_OC2PV = {
    "nomn": "nominative",
    "gent": "genitive",
    "datv": "dative",
    "accs": "accusative",
    "ablt": "instrumental",
    "loct": "prepositional",
}
_ALIAS_CASE = {
    "именительный": "nomn", "родительный": "gent", "дательный": "datv",
    "винительный": "accs", "творительный": "ablt", "предложный": "loct",
}

def _normalize_case(tag_or_name: str) -> Optional[str]:
    t = tag_or_name.strip().lower()
    if t in _OC2PV:
        return t
    return _ALIAS_CASE.get(t)

def lemma(word: str) -> str:
    return _morph.parse(word)[0].normal_form

def is_person_like(token: str) -> bool:
    p = _morph.parse(token)
    return any(g in x.tag for x in p for g in ("Name", "Surn", "Patr"))

def detect_case(token: str) -> Optional[str]:
    p = _morph.parse(token)[0]
    for c in ("nomn", "gent", "datv", "accs", "ablt", "loct"):
        if c in p.tag:
            return c
    return None

def guess_gender_from_token(token: str) -> Optional[str]:
    p = _morph.parse(token)[0]
    if "masc" in p.tag:
        return "masc"
    if "femn" in p.tag:
        return "femn"
    return None

# --- адаптеры к разным enum-ам petrovich ---
def _enum_by_value_or_name(EnumCls, value_str: str):
    """Пробуем Enum(value), затем по имени: UPPER/Cap/low."""
    # 1) по значению
    try:
        return EnumCls(value_str)
    except Exception:
        pass
    # 2) по имени
    members = getattr(EnumCls, "__members__", {})
    for cand in (value_str.upper(), value_str.capitalize(), value_str):
        if cand in members:
            return members[cand]
    # 3) не нашли
    raise ValueError(f"Enum member not found for {EnumCls} <- {value_str}")

def _to_petrovich_case(target_case: str):
    if not _PETROVICH_AVAILABLE:
        return None
    oc = _normalize_case(target_case) or target_case.lower()
    pv = _OC2PV.get(oc)
    if pv is None:
        raise ValueError(f"unsupported case: {target_case}")
    return _enum_by_value_or_name(Case, pv)

def _to_petrovich_gender(g: Optional[str]):
    if not _PETROVICH_AVAILABLE:
        return None
    v = (g or "").lower()
    v = "female" if v.startswith("f") else "male"
    return _enum_by_value_or_name(Gender, v)

def inflect_last(lastname: str, target_case: str, gender: Optional[str] = None) -> str:
    if not _PETROVICH_AVAILABLE:
        return lastname
    try:
        return _pv.lastname(lastname, case=_to_petrovich_case(target_case),
                            gender=_to_petrovich_gender(gender or guess_gender_from_token(lastname)))
    except Exception:
        return lastname

def inflect_first(firstname: str, target_case: str, gender: Optional[str] = None) -> str:
    if not _PETROVICH_AVAILABLE:
        return firstname
    try:
        return _pv.firstname(firstname, case=_to_petrovich_case(target_case),
                             gender=_to_petrovich_gender(gender or guess_gender_from_token(firstname)))
    except Exception:
        return firstname

def inflect_middle(middlename: str, target_case: str, gender: Optional[str] = None) -> str:
    if not _PETROVICH_AVAILABLE:
        return middlename
    try:
        return _pv.middlename(middlename, case=_to_petrovich_case(target_case),
                              gender=_to_petrovich_gender(gender or guess_gender_from_token(middlename)))
    except Exception:
        return middlename

def is_name_token(token: str) -> bool:
    return any("Name" in p.tag for p in _morph.parse(token))

def is_surname_token(token: str) -> bool:
    return any("Surn" in p.tag for p in _morph.parse(token))