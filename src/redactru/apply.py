from __future__ import annotations
"""
Шаг apply: применяет replacement к исходному тексту по документу candidates.json.
Пишет отчёт по схеме report.schema.json. Выполняет выравнивание спанов, если
заданные start/end не совпадают с текстом фрагмента.
"""

import json, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Any

from jsonschema import validate as js_validate

from redactru.util.spans import Span, resolve_overlaps, apply_spans, DEFAULT_PRIORITY

CAND_SCHEMA_PATH = Path("schemas/candidates.schema.json")
REPORT_SCHEMA_PATH = Path("schemas/report.schema.json")


def _read_json(p: Path) -> Dict[str, Any] | List[Dict[str, Any]]:
    return json.loads(p.read_text(encoding="utf-8"))


def _load_candidates_doc(p: Path) -> Dict[str, Any]:
    doc = _read_json(p)
    if not isinstance(doc, dict):
        raise ValueError("candidates: expected object")
    js_validate(instance=doc, schema=json.loads(CAND_SCHEMA_PATH.read_text(encoding="utf-8")))
    return doc


def _align_slice(text: str, start: int, end: int, frag: str) -> Tuple[int, int, bool]:
    """Попробовать выровнять [start,end) под фактическое вхождение frag в text.
    1) Совпадает — возвращаем как есть.
    2) Поиск в окне [start-50 .. start+50+len(frag)].
    3) Фоллбэк — глобальный поиск первого вхождения.
    Если не нашли — возвращаем исходные индексы и ok=False.
    """
    n = len(text)
    s = max(0, start)
    e = min(n, end)
    if 0 <= s <= e <= n and text[s:e] == frag:
        return s, e, True

    # окно вокруг ожидаемого старта
    win_s = max(0, s - 50)
    win_e = min(n, s + 50 + len(frag))
    m = re.search(re.escape(frag), text[win_s:win_e])
    if m:
        ns = win_s + m.start()
        ne = ns + len(frag)
        return ns, ne, True

    # глобально
    m = re.search(re.escape(frag), text)
    if m:
        ns = m.start()
        ne = ns + len(frag)
        return ns, ne, True

    return s, e, False


def apply_to_text(text: str, cand_doc: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Возвращает (новый_текст, report_dict). Выравнивает спаны по содержимому."""
    # Сформировать спаны из документа с выравниванием
    spans: List[Span] = []
    report_items: List[Dict[str, Any]] = []

    for it in cand_doc["items"]:
        if not it.get("apply"):
            # В отчёт тоже попадёт запись о пропуске (ok_slice=True, т.к. не применяли)
            report_items.append({
                "id": it.get("id", f"{it.get('typ')}:{it.get('start')}-{it.get('end')}"),
                "typ": str(it.get("typ")).upper(),
                "start": int(it.get("start", 0)),
                "end": int(it.get("end", 0)),
                "old": str(it.get("text", "")),
                "new": str(it.get("replacement", "")),
                "ok_slice": True,
            })
            continue

        typ = str(it["typ"]).upper()
        raw_text = str(it.get("text", ""))
        s0 = int(it.get("start", 0))
        e0 = int(it.get("end", 0))

        ns, ne, ok = _align_slice(text, s0, e0, raw_text)

        # если нашли — используем выровненные индексы
        if ok:
            spans.append(
                Span(
                    start=ns,
                    end=ne,
                    typ=typ,
                    text=text[ns:ne],
                    replacement=str(it["replacement"]),
                    score=float(it.get("score") or 0.0),
                )
            )
            report_items.append({
                "id": it.get("id", f"{typ}:{ns}-{ne}"),
                "typ": typ,
                "start": ns,
                "end": ne,
                "old": text[ns:ne],
                "new": str(it["replacement"]),
                "ok_slice": True,
            })
        else:
            # не удалось выровнять — пропускаем применение, фиксируем в отчёте
            report_items.append({
                "id": it.get("id", f"{typ}:{s0}-{e0}"),
                "typ": typ,
                "start": s0,
                "end": e0,
                "old": text[s0:e0],
                "new": str(it["replacement"]),
                "ok_slice": False,
            })

    # Снять пересечения и применить
    spans = resolve_overlaps(spans, DEFAULT_PRIORITY)
    new_text, _ops = apply_spans(text, spans)

    report = {
        "version": "1",
        "source_path": "",
        "encoding": "utf-8",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "counts": {
            "total": len(cand_doc["items"]),
            "applied": sum(1 for it in cand_doc["items"] if it.get("apply")),
            "skipped": sum(1 for it in cand_doc["items"] if not it.get("apply")),
        },
        "items": report_items,
    }
    js_validate(instance=report, schema=json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8")))
    return new_text, report


def apply_file(
    input_path: str | Path,
    candidates_path: str | Path,
    out_path: str | Path,
    report_path: str | Path,
    encoding: str = "utf-8",
) -> Tuple[Path, Path]:
    """Полный цикл: прочитать текст, применить, сохранить текст и отчёт. Возвращает пути."""
    inp = Path(input_path)
    cand = Path(candidates_path)
    out_p = Path(out_path)
    rep_p = Path(report_path)

    text = inp.read_text(encoding=encoding, errors="ignore")
    doc = _load_candidates_doc(cand)
    new_text, report = apply_to_text(text, doc)
    report["source_path"] = str(inp.resolve())
    report["encoding"] = encoding

    out_p.parent.mkdir(parents=True, exist_ok=True)
    rep_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(new_text, encoding=encoding)
    rep_p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_p, rep_p
