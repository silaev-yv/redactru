# redactru

CLI-прототип анонимизации русских TXT: ФИО, телефоны, СНИЛС, адреса. Три шага: detect → review → apply. База: regex + словари + морфология. Опция: GPU-NER.

## Быстрый старт (Windows, VS Code)

1. Создать окружение и выбрать его в VS Code:
```powershell
py -3.11 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

2. (Опционально, GPU) Сначала установите PyTorch под вашу CUDA/CPU (см. сайт PyTorch), затем:
```powershell
pip install -r requirements-gpu.txt
```

3. Поместите тестовые тексты в `examples/`:
- `ambiguous_corpus_ru.txt`
- `ambiguous_narrative_ru.txt`

После подготовки можно запустить гибридный анонимизатор:
```powershell
python src/cli/anonymize_hybrid.py examples/ambiguous_corpus_ru.txt --device cpu
```
Параметр `--device` позволяет выбрать `cpu` или `cuda` (по умолчанию определяется автоматически).

## Цели прототипа
- Поиск кандидатов без изменения текста.
- Ручная правка `candidates.csv/.json`.
- Применение токенов `[PER_*]`, `[PHONE_*]`, `[SNILS_*]`, `[ADDR_*]`.

## Планы
- Профили: `ru_regex_only`, `ru_hybrid_gpu`.
- CLI: `redact detect|validate|apply`.
- Мини-тесты и e2e-прогон.
