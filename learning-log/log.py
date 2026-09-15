"""検証可能な学習ログ — ハッシュチェーンで綴る学習証跡（標準ライブラリのみ）

使い方:
    python3 log.py add "RAGのk掃引を実測し欠落項目を数えた" --min 90 --tag rag --file out_k3.txt
    python3 log.py backfill ~/Downloads --ext .txt   # 既存ファイル群を事後登録として一括記録
    python3 log.py verify                            # チェーンの検証
    python3 log.py report                            # report.html を生成

チェーンが保証するのは「各記録が、記録した時点以降改ざんされていないこと」。
学習した日付そのものの真実性は保証しない（事後登録は backfill と明示される）。
この正直さが信用の土台なので、偽装しないこと。
"""
import argparse
import datetime
import hashlib
import html
import json
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).parent
LOG_FILE = BASE_DIR / "learning-log.jsonl"
REPORT_FILE = BASE_DIR / "report.html"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _last_hash() -> str | None:
    if not LOG_FILE.exists():
        return None
    last = None
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = line.strip()
    return _sha256_text(last) if last else None


def _append(record: dict) -> dict:
    record["prev"] = _last_hash()
    record["record_hash"] = _sha256_text(
        json.dumps(record, ensure_ascii=False, sort_keys=True))
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _file_info(path: pathlib.Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": stat.st_size,
        "mtime": datetime.datetime.fromtimestamp(stat.st_mtime)
                 .astimezone().isoformat(timespec="seconds"),
    }


def cmd_add(args) -> None:
    record = {
        "type": "entry",
        "timestamp": _now(),
        "text": args.text,
        "minutes": args.min,
        "tags": args.tag or [],
        "backfill": False,
    }
    if args.file:
        record["artifact"] = _file_info(pathlib.Path(args.file))
    _append(record)
    print(f"記録しました: {record['text']} ({record['minutes']}分)")


def cmd_backfill(args) -> None:
    folder = pathlib.Path(args.folder).expanduser()
    files = sorted(
        (p for p in folder.iterdir()
         if p.is_file() and (not args.ext or p.suffix.lower() in args.ext)),
        key=lambda p: p.stat().st_mtime)
    if not files:
        sys.exit(f"{folder} に対象ファイルがありません。")
    for p in files:
        _append({
            "type": "entry",
            "timestamp": _now(),
            "text": f"既存成果物の事後登録: {p.name}",
            "minutes": 0,
            "tags": ["backfill"],
            "backfill": True,
            "artifact": _file_info(p),
        })
    print(f"{len(files)} 件を事後登録しました（backfill として明示されます）。")


def cmd_verify(quiet: bool = False) -> list[dict]:
    if not LOG_FILE.exists():
        sys.exit("learning-log.jsonl がありません。")
    prev = None
    records = []
    lines = [l for l in LOG_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    for i, line in enumerate(lines, 1):
        rec = json.loads(line)
        body = dict(rec)
        claimed = body.pop("record_hash")
        if claimed != _sha256_text(json.dumps(body, ensure_ascii=False, sort_keys=True)):
            sys.exit(f"[NG] レコード{i}: 内容が record_hash と一致しません（改ざんの疑い）")
        if rec["prev"] != prev:
            sys.exit(f"[NG] レコード{i}: チェーンが途切れています（削除・並べ替えの疑い）")
        prev = _sha256_text(line.strip())
        records.append(rec)
    if not quiet:
        print(f"検証完了: 全{len(records)}件、チェーンは無傷です。")
    return records


def cmd_report(args) -> None:
    records = cmd_verify(quiet=True)
    entries = [r for r in records if r["type"] == "entry"]
    live = [r for r in entries if not r["backfill"]]
    total_min = sum(r["minutes"] for r in live)
    by_tag: dict[str, int] = {}
    for r in live:
        for t in (r["tags"] or ["(タグなし)"]):
            by_tag[t] = by_tag.get(t, 0) + r["minutes"]

    def row(r: dict) -> str:
        art = ""
        if "artifact" in r:
            a = r["artifact"]
            art = (f'<div class="art">成果物: {html.escape(a["name"])} '
                   f'({a["size"]:,}B, 更新 {a["mtime"][:10]}) '
                   f'<code>{a["sha256"][:16]}…</code></div>')
        badge = '<span class="bf">事後登録</span> ' if r["backfill"] else ""
        mins = f'{r["minutes"]}分' if r["minutes"] else "—"
        return (f'<li><span class="ts">{r["timestamp"][:16].replace("T", " ")}</span> '
                f'{badge}{html.escape(r["text"])} '
                f'<span class="min">{mins}</span>'
                f'<span class="tags">{" ".join("#" + html.escape(t) for t in r["tags"] if t != "backfill")}</span>'
                f'{art}</li>')

    tag_rows = "".join(
        f"<tr><td>#{html.escape(t)}</td><td>{m // 60}時間{m % 60:02d}分</td></tr>"
        for t, m in sorted(by_tag.items(), key=lambda kv: -kv[1]))

    doc = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>学習証跡レポート</title>
<style>
  body {{ margin:0; padding:32px 16px; background:#f5f4f0; color:#23211d;
         font-family:"Hiragino Sans","Yu Gothic","Noto Sans JP",sans-serif;
         line-height:1.75; font-size:15px; }}
  main {{ max-width:760px; margin:0 auto; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .lead {{ color:#6f6a60; font-size:13px; margin:0 0 20px; }}
  .card {{ background:#fff; border:1px solid #e2dfd8; border-radius:10px;
           padding:18px 20px; margin-bottom:14px; }}
  .ok {{ display:inline-block; background:#2f5d3a; color:#fff; font-size:12px;
         font-weight:700; padding:2px 12px; border-radius:999px; }}
  table {{ border-collapse:collapse; }} td {{ padding:2px 16px 2px 0; }}
  ul {{ list-style:none; margin:0; padding:0; }}
  li {{ padding:8px 0; border-bottom:1px dashed #e2dfd8; }}
  .ts {{ color:#6f6a60; font-size:12.5px; margin-right:6px; }}
  .min {{ color:#2f5d3a; font-size:12.5px; margin-left:8px; }}
  .tags {{ color:#6f6a60; font-size:12.5px; margin-left:8px; }}
  .bf {{ background:#8a5a1e; color:#fff; font-size:11px; padding:1px 8px;
         border-radius:999px; }}
  .art {{ font-size:12.5px; color:#6f6a60; }}
  code {{ font-size:11.5px; }}
  footer {{ color:#6f6a60; font-size:12px; margin-top:20px; }}
</style></head><body><main>
<h1>学習証跡レポート</h1>
<p class="lead">生成: {_now()[:16].replace("T", " ")} ／ このレポートは learning-log.jsonl から機械生成されたもの。</p>
<div class="card">
  <span class="ok">チェーン検証済み ✓ 全{len(records)}件</span>
  <p>記録期間: {entries[0]["timestamp"][:10]} 〜 {entries[-1]["timestamp"][:10]} ／
  学習記録 {len(live)}件（計 {total_min // 60}時間{total_min % 60:02d}分）＋ 事後登録 {len(entries) - len(live)}件</p>
  <table>{tag_rows}</table>
</div>
<div class="card"><ul>{"".join(row(r) for r in reversed(entries))}</ul></div>
<footer>このチェーンが保証するのは「各記録が、記録した時点以降改ざんされていないこと」。
学習日そのものの真実性は保証せず、事後登録は明示している。原本の検証は
<code>python3 log.py verify</code> で誰でも再実行できる。</footer>
</main></body></html>"""
    REPORT_FILE.write_text(doc, encoding="utf-8")
    print(f"生成しました: {REPORT_FILE.name}（{len(entries)}件、計{total_min // 60}時間{total_min % 60:02d}分）")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="学習を1件記録する")
    a.add_argument("text")
    a.add_argument("--min", type=int, default=0, help="学習時間（分）")
    a.add_argument("--tag", action="append", help="タグ（複数可）")
    a.add_argument("--file", help="成果物ファイル（ハッシュを一緒に記録）")
    a.set_defaults(func=cmd_add)

    b = sub.add_parser("backfill", help="既存ファイル群を事後登録する")
    b.add_argument("folder")
    b.add_argument("--ext", action="append", help="対象拡張子（例: --ext .txt）")
    b.set_defaults(func=cmd_backfill)

    v = sub.add_parser("verify", help="チェーンを検証する")
    v.set_defaults(func=lambda args: cmd_verify())

    r = sub.add_parser("report", help="report.html を生成する")
    r.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
