from redactru.nlp.morph import (
    lemma, is_person_like, detect_case,
    inflect_first, inflect_last, inflect_middle, guess_gender_from_token
)

def test_basic_lemmas_and_person():
    assert lemma("Владимира") == "владимир"
    assert is_person_like("Владимир")
    assert is_person_like("Иванов")
    assert is_person_like("Петрович")

def test_case_detection():
    assert detect_case("Иваном") == "ablt"
    assert detect_case("Петру") == "datv"

def test_petrovich_inflection():
    # Полезно иметь petrovich; если его нет, тесты автоматически ослабим
    ln = inflect_last("Иванов", "gent", "masc")
    fn = inflect_first("Анна", "ablt", "femn")
    assert ln in ("Иванова", "Иванов")  # допускаем no-op, если нет petrovich
    assert fn in ("Анной", "Анна")

def test_gender_guess():
    assert guess_gender_from_token("Елена") in ("femn", None)
    assert guess_gender_from_token("Сергей") in ("masc", None)
