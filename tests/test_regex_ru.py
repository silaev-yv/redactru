import re
from redactru.rules.regex_ru import (
    iter_person_spans, has_address_markers, iter_address_markers, iter_address_spans
)

def test_person_basic_patterns():
    txt = "Выступал Иванов И.И., затем Анна-Мария де Ла Крус и Пётр Сидоров."
    spans = [s.raw for s in iter_person_spans(txt)]
    # Есть фамилия с инициалами и дефисная фамилия с частицей
    assert any("Иванов И.И." in r for r in spans)
    assert any("Анна-Мария де Ла Крус" in r for r in spans) or any("Пётр Сидоров" in r for r in spans)

def test_address_markers_detection():
    s = "Республика Татарстан, г. Казань, ул. Ленина, д. 5, кв. 3"
    assert has_address_markers(s)
    tokens = [t.token for t in iter_address_markers(s)]
    # Проверяем наличие ключевых маркеров
    assert "Республика" in tokens
    assert "г." in tokens
    assert "ул." in tokens
    assert "д." in tokens

def test_address_spans_coarse():
    s = "Доставка: Республика Татарстан, г. Казань, пр-кт Победы, д 1."
    chunks = list(iter_address_spans(s))
    assert len(chunks) >= 1
    assert "Казань" in chunks[0].raw

def test_address_with_tail_components():
    s = "Новый офис: обл. Томская, р-н Ленинский, г. Томск, ул. Ленина, д 5 к 1 стр 2 кв 10."
    chunks = list(iter_address_spans(s))
    assert len(chunks) >= 1
    assert "д 5" in chunks[0].raw and "к 1" in chunks[0].raw and "стр 2" in chunks[0].raw and "кв 10" in chunks[0].raw
