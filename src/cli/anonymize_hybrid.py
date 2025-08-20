import json, argparse, sys
from pathlib import Path
from hybrid.aggregator import HybridAnonymizer

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", help="входной файл .txt")
    p.add_argument("--out", default=None, help="выходной .jsonl со спанами")
    p.add_argument("--device", choices=["cpu", "cuda"], default=None,
                   help="устройство для NER: cpu или cuda (по умолчанию авто)")
    args = p.parse_args()

    text = Path(args.path).read_text(encoding="utf-8")
    az = HybridAnonymizer(device=args.device)
    spans = az.process(text)

    out = args.out or (Path(args.path).with_suffix(".hybrid.jsonl"))
    with open(out, "w", encoding="utf-8") as f:
        for s in spans:
            f.write(json.dumps({
                "start": s.start, "end": s.end, "text": s.text,
                "type": s.type, "score": round(s.score, 4), "meta": s.meta
            }, ensure_ascii=False) + "\n")
    print(f"ok: {out}")

if __name__ == "__main__":
    main()
