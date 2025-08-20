from pathlib import Path
import json
from jsonschema import validate as js_validate

from redactru.validate import build_candidates_document, _read_schema

def test_build_candidates_document(tmp_path: Path):
    raw = [
        # валидный СНИЛС -> apply True
        {"id":"SNILS:0-14","typ":"SNILS","start":0,"end":14,"text":"112-233-445 95","norm":"112-233-445 95","score":1.0,"meta":{"valid":True}},
        # телефон -> apply True
        {"id":"PHONE:16-33","typ":"PHONE","start":16,"end":33,"text":"+7 (999) 123-45-67","norm":"+79991234567","score":0.9,"meta":{"digits":"79991234567"}},
        # адрес -> apply False
        {"id":"ADDR:35-70","typ":"ADDR","start":35,"end":70,"text":"г. Казань, ул. Ленина, д 5","norm":None,"score":0.7,"meta":{}},
        # ФИО -> apply False
        {"id":"PER:80-92","typ":"PER","start":80,"end":92,"text":"Иванов И.И.","score":0.5,"meta":{"kind":"regex"}},
    ]
    mapping = tmp_path / "mapping.json"
    doc = build_candidates_document(raw, mapping)
    js_validate(doc, _read_schema())
    assert doc["version"] == "1"
    items = doc["items"]
    types = {i["typ"] for i in items}
    assert {"SNILS","PHONE","ADDR","PER"} <= types
    # правила по умолчанию
    by = {i["typ"]: i for i in items}
    assert by["SNILS"]["apply"] is True
    assert by["PHONE"]["apply"] is True
    assert by["ADDR"]["apply"] is False
    assert by["PER"]["apply"] is False
    # токены с правильными префиксами
    assert by["PHONE"]["replacement"].startswith("[PHONE_")
    assert by["ADDR"]["replacement"].startswith("[ADDR_")
    # mapping.json создан
    assert mapping.exists()
