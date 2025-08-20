from __future__ import annotations
import json, csv
from pathlib import Path
import typer

from redactru.detect import detect_file
from redactru.validate import validate_file
from redactru.apply import apply_file

app = typer.Typer(add_completion=False, no_args_is_help=True)

@app.command("detect")
def cmd_detect(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("candidates_raw.json"), "--out", "-o"),
    preview: Path | None = typer.Option(None, "--preview", "-p"),
    encoding: str = typer.Option("utf-8", "--encoding"),
):
    """Найти кандидатов и сохранить «сырые» результаты (JSON). CSV-превью опционально."""
    cs = detect_file(str(input_path), encoding=encoding)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in cs], ensure_ascii=False, indent=2), encoding="utf-8")
    if preview:
        preview.parent.mkdir(parents=True, exist_ok=True)
        with preview.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["id","type","start","end","text","norm","score"])
            for c in cs:
                w.writerow([c.id, c.typ, c.start, c.end, c.text, c.norm or "", f"{c.score:.2f}"])
    typer.echo(f"written: {out}")
    if preview:
        typer.echo(f"preview: {preview}")

@app.command("validate")
def cmd_validate(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("candidates.json"), "--out", "-o"),
    mapping: Path = typer.Option(Path("mapping.json"), "--mapping"),
    export: Path | None = typer.Option(None, "--export-csv", help="Экспортировать валидированный документ в CSV с колонками apply/replacement для ручного редактирования"),
):
    res = validate_file(input_path, out, mapping)
    typer.echo(f"validated: {res}")
    typer.echo(f"mapping: {mapping}")
    if export:
        doc = json.loads(Path(res).read_text(encoding="utf-8"))
        export.parent.mkdir(parents=True, exist_ok=True)
        with export.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["id","type","start","end","text","norm","score","apply","replacement"])
            for it in doc["items"]:
                w.writerow([
                    it["id"], it["typ"], it["start"], it["end"],
                    it["text"], it.get("norm") or "", f"{it.get('score',0):.2f}",
                    "true" if it.get("apply") else "false",
                    it.get("replacement","")
                ])
        typer.echo(f"exported csv: {export}")

@app.command("apply")
def cmd_apply(
    input_text: Path = typer.Argument(..., exists=True, readable=True),
    candidates: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("out.txt"), "--out", "-o"),
    report: Path = typer.Option(Path("report.json"), "--report"),
    encoding: str = typer.Option("utf-8", "--encoding"),
):
    """Применить замены по candidates.json к исходному тексту. Сохранить текст и отчёт."""
    out_p, rep_p = apply_file(input_text, candidates, out, report, encoding=encoding)
    typer.echo(f"out: {out_p}")
    typer.echo(f"report: {rep_p}")

if __name__ == "__main__":
    app()
