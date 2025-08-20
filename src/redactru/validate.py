from __future__ import annotations
"""
Преобразование результатов detect (JSON или CSV) в валидированный документ candidates.json по схеме.
Добавляет поля: apply, replacement. Токены — через TokenManager (mapping.json).

Правила по умолчанию:
- SNILS: apply = True, если meta.valid == True
- PHONE: apply = True
- ADDR, PER: apply = False (для ручной проверки)

CSV поддерживается формата превью из CLI detect: ;-разделитель, с колонками:
id;type;start;end;text;norm;score[;apply][;replacement]
"""

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Dict, Any

from jsonschema import validate as js_validate

from redactru.util.tokens import TokenManager


SCHEMA_PATH = Path("schemas/candidates.schema.json")


def _read_schema() -> Dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_items_from_json(p: Path) -> List[Dict[str, Any]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "items" in data:
        return list(data["items"])
    if isinstance(data, list):
        # это «сырые» кандидаты из detect
        return list(data)
    raise ValueError("Unsupported JSON structure")


def _load_items_from_csv(p: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            if not row.get("id"):
                continue
            out.append(
                {
                    "id": row.get("id"),
                    "typ": row.get("type") or row.get("typ"),
                    "start": int(row.get("start", 0)),
                    "end": int(row.get("end", 0)),
                    "text": row.get("text", ""),
                    "norm": row.get("norm") or None,
                    "score": float(row.get("score", 0) or 0),
                    # apply/replacement могут быть заданы пользователем
                    "apply": _coerce_bool(row.get("apply")) if "apply" in row else None,
                    "replacement": row.get("replacement") if "replacement" in row else None,
                    "meta": {},  # превью CSV не тащит meta — оставляем пустым
                }
            )
    return out


def _coerce_bool(v: Any) -> bool | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("1", "true", "t", "y", "yes", "да"):
        return True
    if s in ("0", "false", "f", "n", "no", "нет"):
        return False
    return None


def _default_apply(item: Dict[str, Any]) -> bool:
    t = (item.get("typ") or "").upper()
    if t == "SNILS":
        # meta.valid может отсутствовать, тогда осторожно
        valid = False
        meta = item.get("meta") or {}
        if isinstance(meta, dict):
            valid = bool(meta.get("valid"))
        return valid
    if t == "PHONE":
        return True
    return False  # ADDR, PER — ручная валидация по умолчанию


def _token_key(item: Dict[str, Any]) -> str:
    # ключ для детерминизма: нормализованная форма, если есть; иначе «сырой» текст
    return (item.get("norm") or item.get("text") or "").strip()


def _token_type(item: Dict[str, Any]) -> str:
    return (item.get("typ") or "").upper()


def build_candidates_document(
    raw_items: Iterable[Dict[str, Any]],
    mapping_path: Path,
) -> Dict[str, Any]:
    """
    Преобразовать список «сырых» кандидатов (из detect JSON или CSV превью) к документу по схеме.
    Создаёт/обновляет mapping.json и заполняет replacement токенами.
    """
    tm = TokenManager(mapping_path)

    items: List[Dict[str, Any]] = []
    for it in raw_items:
        typ = _token_type(it)
        if typ not in {"SNILS", "PHONE", "ADDR", "PER"}:
            continue

        apply_flag = it.get("apply")
        if apply_flag is None:
            apply_flag = _default_apply(it)

        replacement = it.get("replacement")
        if not replacement:
            key = _token_key(it) or f"{typ}:{it.get('start')}-{it.get('end')}"
            replacement = tm.get(typ, key)

        items.append(
            {
                "id": it.get("id") or f"{typ}:{it.get('start')}-{it.get('end')}",
                "typ": typ,
                "start": int(it.get("start", 0)),
                "end": int(it.get("end", 0)),
                "text": it.get("text", ""),
                "norm": it.get("norm") if it.get("norm") else None,
                "score": float(it.get("score", 0) or 0.0),
                "apply": bool(apply_flag),
                "replacement": replacement,
                "meta": it.get("meta") or {},
            }
        )

    doc = {"version": "1", "items": items}
    js_validate(instance=doc, schema=_read_schema())
    return doc


def validate_file(
    input_path: str | Path,
    out_path: str | Path,
    mapping_path: str | Path = "mapping.json",
) -> Path:
    """
    Загрузить кандидатов из JSON или CSV, построить документ по схеме и сохранить.
    Возвращает путь к out_path.
    """
    in_p = Path(input_path)
    if not in_p.exists():
        raise FileNotFoundError(in_p)
    if in_p.suffix.lower() == ".csv":
        raw = _load_items_from_csv(in_p)
    else:
        raw = _load_items_from_json(in_p)

    doc = build_candidates_document(raw, Path(mapping_path))
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_p
