"""Генерация детерминированных токенов вида [PER_001], [PHONE_002] и карта соответствий.

Логика:
- Токен однозначно определяется парой (type, key).
- При первом запросе пары создаётся новый индекс по типу и токен [TYPE_###].
- Карта хранится на диске в JSON. Повторный запуск сохраняет нумерацию.

Типы по умолчанию: PER, PHONE, SNILS, ADDR.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple

_ALLOWED = {"PER", "PHONE", "SNILS", "ADDR"}

def _slug_key(key: str) -> str:
    """Нормализованный ключ (для устойчивого совпадения)."""
    k = key.strip().lower()
    k = re.sub(r"\s+", " ", k)
    return k

def _next_label(n: int) -> str:
    return f"{n:03d}"

@dataclass
class TokenManager:
    path: Path
    tokens: Dict[str, Dict[str, str]] = field(default_factory=dict)   # {type: {key: token}}
    counters: Dict[str, int] = field(default_factory=dict)            # {type: last_index}

    def __post_init__(self) -> None:
        if self.path.exists():
            self._load()
        for t in _ALLOWED:
            self.tokens.setdefault(t, {})
            self.counters.setdefault(t, self._scan_max_index(t))

    # ---- public API ----

    def get(self, typ: str, key: str) -> str:
        """Вернуть токен для пары (typ, key). Создать при отсутствии."""
        t = typ.upper()
        if t not in _ALLOWED:
            raise ValueError(f"unsupported token type: {typ}")
        skey = _slug_key(key)
        tok = self.tokens[t].get(skey)
        if tok:
            return tok
        # новый
        idx = self.counters[t] + 1
        self.counters[t] = idx
        tok = f"[{t}_{_next_label(idx)}]"
        self.tokens[t][skey] = tok
        self._save()
        return tok

    def lookup(self, typ: str, key: str) -> str | None:
        """Только найти, не создавая."""
        t = typ.upper()
        if t not in _ALLOWED:
            return None
        return self.tokens.get(t, {}).get(_slug_key(key))

    def all_items(self) -> Dict[str, Dict[str, str]]:
        """Глубокая копия словаря (для отчётов)."""
        return {t: dict(kv) for t, kv in self.tokens.items()}

    # ---- io ----

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        self.tokens = data.get("tokens", {})
        self.counters = data.get("counters", {})

    def _save(self) -> None:
        data = {"tokens": self.tokens, "counters": self.counters}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- helpers ----

    def _scan_max_index(self, typ: str) -> int:
        """Определить максимальный индекс по уже сохранённым токенам типа."""
        max_i = 0
        for tok in self.tokens.get(typ, {}).values():
            m = re.search(rf"^\[{typ}_(\d{{3}})\]$", tok)
            if m:
                max_i = max(max_i, int(m.group(1)))
        return max_i
