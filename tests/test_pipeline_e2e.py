from pathlib import Path
import json

from redactru.validate import build_candidates_document
from redactru.apply import apply_to_text

def test_e2e_apply_from_validated_doc(tmp_path: Path):
    # Исходный текст
    txt = "СНИЛС 112-233-445 95; Тел: +7 (999) 123-45-67; г. Казань, ул. Ленина, д 5; Иванов И.И."
    # «Сырые» кандидаты (как будто из detect)
    raw = [
        {"id":"SNILS:7-21","typ":"SNILS","start":7,"end":21,"text":"112-233-445 95","norm":"112-233-445 95","score":1.0,"meta":{"valid":True}},
        {"id":"PHONE:28-51","typ":"PHONE","start":28,"end":51,"text":"+7 (999) 123-45-67","norm":"+79991234567","score":0.9,"meta":{"digits":"79991234567"}},
        {"id":"ADDR:53-84","typ":"ADDR","start":53,"end":84,"text":"г. Казань, ул. Ленина, д 5","score":0.7,"meta":{}},
        {"id":"PER:86-97","typ":"PER","start":86,"end":97,"text":"Иванов И.И.","score":0.5,"meta":{"kind":"regex"}},
    ]
    mapping = tmp_path / "mapping.json"
    doc = build_candidates_document(raw, mapping)

    # Применение
    new_text, report = apply_to_text(txt, doc)

    # Проверки
    assert "[SNILS_" in new_text
    assert "[PHONE_" in new_text
    # По умолчанию ADDR и PER не применяются
    assert "г. Казань" in new_text and "Иванов И.И." in new_text

    assert report["version"] == "1"
    assert report["counts"]["applied"] >= 2
    assert report["counts"]["skipped"] >= 2
    # В отчёте совпадает вырезанный old с фактическим
    assert all(item["ok_slice"] for item in report["items"])
