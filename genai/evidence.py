"""非送信証跡（オフライン実行の証明ログ）

ask.py の実行ごとに evidence.jsonl へ1行追記する。各レコードには
  - 外部ネットワーク疎通チェックの結果（失敗していれば = オフライン実行の証拠）
  - 質問・回答・index.json・コード自体の SHA-256 ハッシュ
  - 直前レコードのハッシュ（ハッシュチェーン。後からの改ざん・差し替えを検出できる）
が入る。

検証:
    python3 evidence.py --verify
"""
import datetime
import hashlib
import json
import pathlib
import socket
import sys

import config

BASE_DIR = pathlib.Path(__file__).parent
EVIDENCE_FILE = BASE_DIR / "evidence.jsonl"

# 外部疎通チェック先。TCP接続の試行のみでデータは一切送らない。
# 全て失敗する = 外部ネットワークから遮断された状態で実行された、の証拠になる。
PROBES = [
    ("1.1.1.1", 443),   # Cloudflare
    ("8.8.8.8", 53),    # Google DNS
]
DNS_PROBE = "example.com"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256(text.encode("utf-8"))


def check_network() -> dict:
    """外部への疎通を試し、結果を記録する（データ送信はしない）"""
    probes = []
    for host, port in PROBES:
        try:
            with socket.create_connection((host, port), timeout=2):
                probes.append({"target": f"{host}:{port}", "reachable": True})
        except OSError as e:
            probes.append({"target": f"{host}:{port}", "reachable": False,
                           "error": type(e).__name__})
    try:
        socket.getaddrinfo(DNS_PROBE, 443)
        probes.append({"target": f"dns:{DNS_PROBE}", "reachable": True})
    except OSError as e:
        probes.append({"target": f"dns:{DNS_PROBE}", "reachable": False,
                       "error": type(e).__name__})
    return {"probes": probes,
            "offline": all(not p["reachable"] for p in probes)}


def _last_record_hash() -> str | None:
    if not EVIDENCE_FILE.exists():
        return None
    last = None
    with EVIDENCE_FILE.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = line
    return _sha256_text(last.strip()) if last else None


def append_record(question: str, answer: str) -> dict:
    """1回の質問応答の証跡を evidence.jsonl に追記する"""
    code_hashes = {
        name: _sha256((BASE_DIR / name).read_bytes())
        for name in ("config.py", "llm.py", "ingest.py", "ask.py", "evidence.py")
        if (BASE_DIR / name).exists()
    }
    index_file = BASE_DIR / "index.json"
    record = {
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "network": check_network(),
        "provider": {
            "name": config.PROVIDER,
            "base_url": config.BASE_URL,
            "chat_model": config.CHAT_MODEL,
            "embed_model": config.EMBED_MODEL,
        },
        "hashes": {
            "question": _sha256_text(question),
            "answer": _sha256_text(answer),
            "index.json": _sha256(index_file.read_bytes()) if index_file.exists() else None,
            "code": code_hashes,
        },
        "prev": _last_record_hash(),
    }
    record["record_hash"] = _sha256_text(
        json.dumps(record, ensure_ascii=False, sort_keys=True)
    )
    with EVIDENCE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def verify() -> None:
    """ハッシュチェーンを検証する"""
    if not EVIDENCE_FILE.exists():
        sys.exit("evidence.jsonl がありません。")
    prev_hash = None
    lines = [l for l in EVIDENCE_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    for i, line in enumerate(lines, 1):
        rec = json.loads(line)
        claimed = rec.pop("record_hash")
        actual = _sha256_text(json.dumps(rec, ensure_ascii=False, sort_keys=True))
        if claimed != actual:
            sys.exit(f"[NG] レコード{i}: 内容が record_hash と一致しません（改ざんの疑い）")
        if rec["prev"] != prev_hash:
            sys.exit(f"[NG] レコード{i}: チェーンが途切れています（削除・並べ替えの疑い）")
        prev_hash = _sha256_text(line.strip())
        offline = "オフライン" if rec["network"]["offline"] else "オンライン"
        print(f"[OK] レコード{i}: {rec['timestamp']}  {offline}実行  "
              f"model={rec['provider']['chat_model']}")
    print(f"検証完了: 全{len(lines)}件、チェーンは無傷です。")


if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify()
    else:
        print(__doc__)
