"""モデルファイルの受け入れ検査（標準ライブラリのみ・ファイルを「実行せずに」調べる）

使い方:
    python3 modelcheck.py <モデルファイル>
    python3 modelcheck.py <モデルファイル> --expect-sha256 <64桁ハッシュ>
    python3 modelcheck.py <モデルファイル> --record "https://huggingface.co/..." # 取得記録を追記

方針:
  - pickle系（.pt .pth .bin .pkl .ckpt）は中身を開かず「不合格」。読み込み時に
    任意コードが実行される形式であり、スキャナにも迂回脆弱性が見つかっている
  - GGUF / safetensors はヘッダを構文解析して中身の素性（アーキテクチャ、
    ライセンス等）を表示する。どちらもコードを含まないデータ形式
  - 実行環境のメモリと突き合わせ、「そもそも載るか」を判定する
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import struct
import sys

BASE_DIR = pathlib.Path(__file__).parent
RECORD_FILE = BASE_DIR / "models.jsonl"

PICKLE_EXTS = {".pt", ".pth", ".bin", ".pkl", ".ckpt"}
META_READ_CAP = 64 * 1024 * 1024  # メタデータ走査の上限（異常なファイル対策）

OK, NG, WARN = "[OK]", "[NG]", "[注意]"


# ---------- GGUF ----------

def _read(f, n, budget):
    budget[0] += n
    if budget[0] > META_READ_CAP:
        raise ValueError("メタデータが異常に大きい（走査上限超過）")
    data = f.read(n)
    if len(data) != n:
        raise ValueError("ファイルが途中で終わっている")
    return data


def _gguf_string(f, budget):
    (n,) = struct.unpack("<Q", _read(f, 8, budget))
    return _read(f, n, budget).decode("utf-8", errors="replace")


def _gguf_value(f, vtype, budget):
    scalar = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i",
              6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
    if vtype in scalar:
        fmt = scalar[vtype]
        (v,) = struct.unpack(fmt, _read(f, struct.calcsize(fmt), budget))
        return v
    if vtype == 8:
        return _gguf_string(f, budget)
    if vtype == 9:  # 配列: 中身は読み飛ばす（トークナイザ語彙などは巨大）
        (itype,) = struct.unpack("<I", _read(f, 4, budget))
        (count,) = struct.unpack("<Q", _read(f, 8, budget))
        for _ in range(count):
            _gguf_value(f, itype, budget)
        return f"<配列 {count}件>"
    raise ValueError(f"未知の値型 {vtype}")


def inspect_gguf(path: pathlib.Path) -> list[str]:
    lines = []
    budget = [0]
    with path.open("rb") as f:
        if _read(f, 4, budget) != b"GGUF":
            return [f"{NG} 拡張子は .gguf だが GGUF のマジックナンバーがない（偽装の疑い）"]
        (version,) = struct.unpack("<I", _read(f, 4, budget))
        (n_tensors,) = struct.unpack("<Q", _read(f, 8, budget))
        (n_kv,) = struct.unpack("<Q", _read(f, 8, budget))
        lines.append(f"{OK} GGUF形式（version {version} / テンソル {n_tensors:,}個）")
        if version not in (2, 3):
            lines.append(f"{WARN} 珍しいGGUFバージョン({version})。実行系の対応を確認")
        meta = {}
        try:
            for _ in range(n_kv):
                key = _gguf_string(f, budget)
                (vtype,) = struct.unpack("<I", _read(f, 4, budget))
                val = _gguf_value(f, vtype, budget)
                if not key.startswith("tokenizer."):
                    meta[key] = val
        except ValueError as e:
            lines.append(f"{NG} メタデータの解析に失敗: {e}")
            return lines
    show = ["general.architecture", "general.name", "general.license",
            "general.quantization_version", "general.file_type",
            "general.source.url", "general.source.huggingface.repository"]
    for k in show:
        if k in meta:
            lines.append(f"    {k} = {meta[k]}")
    ctx = [k for k in meta if k.endswith(".context_length")]
    for k in ctx:
        lines.append(f"    {k} = {meta[k]:,}")
    if "general.license" not in meta:
        lines.append(f"{WARN} ライセンス情報がメタデータにない。配布元ページで必ず確認")
    return lines


# ---------- safetensors ----------

def inspect_safetensors(path: pathlib.Path) -> list[str]:
    lines = []
    with path.open("rb") as f:
        (hlen,) = struct.unpack("<Q", f.read(8))
        if hlen > META_READ_CAP:
            return [f"{NG} ヘッダ長が異常（{hlen:,}バイト）"]
        try:
            header = json.loads(f.read(hlen).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return [f"{NG} safetensorsヘッダがJSONとして読めない（偽装・破損の疑い）"]
    tensors = {k: v for k, v in header.items() if k != "__metadata__"}
    dtypes = sorted({v.get("dtype", "?") for v in tensors.values()})
    lines.append(f"{OK} safetensors形式（テンソル {len(tensors):,}個 / dtype: {', '.join(dtypes)}）")
    lines.append(f"    ※形式自体は安全でも、読み込む側の config.json / trust_remote_code 経由の")
    lines.append(f"      実行があり得る。README のチェックリスト A-4 を参照")
    return lines


# ---------- 共通 ----------

def memory_fit(size: int) -> list[str]:
    meminfo = pathlib.Path("/proc/meminfo")
    if not meminfo.exists():
        return [f"{WARN} メモリ情報を取得できない環境（Windows直下等）。手動で確認を"]
    kv = {}
    for line in meminfo.read_text().splitlines():
        k, _, v = line.partition(":")
        kv[k.strip()] = int(v.strip().split()[0]) * 1024  # kB -> B
    total, avail = kv.get("MemTotal", 0), kv.get("MemAvailable", 0)
    need = int(size * 1.2)  # 実行時はコンテキスト等で1〜2割膨らむ
    lines = [f"    モデル {size / 2**30:.2f} GiB / メモリ 合計 {total / 2**30:.1f} GiB・"
             f"利用可能 {avail / 2**30:.1f} GiB（必要目安 {need / 2**30:.2f} GiB）"]
    if need > total:
        lines.append(f"{NG} この環境の合計メモリに載らない。量子化を上げるか小さいモデルへ")
    elif need > avail:
        lines.append(f"{WARN} 現在の空きでは不足。他のモデル・アプリを止めれば載る可能性")
    else:
        lines.append(f"{OK} メモリに収まる見込み")
    return lines


def record(path: pathlib.Path, sha256: str, url: str | None) -> None:
    prev = None
    if RECORD_FILE.exists():
        lines = [l for l in RECORD_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
        if lines:
            prev = hashlib.sha256(lines[-1].encode("utf-8")).hexdigest()
    rec = {
        "timestamp": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "file": path.name, "size": path.stat().st_size,
        "sha256": sha256, "source_url": url, "prev": prev,
    }
    rec["record_hash"] = hashlib.sha256(
        json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    with RECORD_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"\n取得記録を {RECORD_FILE.name} に追記しました。")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file")
    p.add_argument("--expect-sha256", help="配布元が公表しているSHA-256と照合")
    p.add_argument("--record", nargs="?", const="", metavar="URL",
                   help="取得記録（ハッシュチェーン）を models.jsonl に追記")
    args = p.parse_args()

    path = pathlib.Path(args.file).expanduser()
    if not path.is_file():
        sys.exit(f"{NG} ファイルがありません: {path}")

    print(f"=== 受け入れ検査: {path.name} ===")
    ext = path.suffix.lower()

    if ext in PICKLE_EXTS:
        print(f"{NG} pickle系形式（{ext}）。読み込み時に任意コードが実行され得るため不合格。")
        print(f"    同じモデルの GGUF 版か safetensors 版を探すこと。")
        print(f"    ※スキャナ(PickleScan等)にも迂回脆弱性が見つかっており「スキャン済み」は安全の保証にならない")
        sys.exit(1)

    print("ハッシュ計算中...")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    sha = h.hexdigest()
    print(f"    SHA-256 = {sha}")
    if args.expect_sha256:
        if sha == args.expect_sha256.lower():
            print(f"{OK} 公表ハッシュと一致")
        else:
            print(f"{NG} 公表ハッシュと不一致。取得し直すこと（改ざん・破損の疑い）")
            sys.exit(1)

    if ext == ".gguf":
        for line in inspect_gguf(path):
            print(line)
    elif ext == ".safetensors":
        for line in inspect_safetensors(path):
            print(line)
    else:
        print(f"{WARN} 未知の拡張子（{ext}）。GGUF/safetensors 以外は原則受け入れない")

    for line in memory_fit(path.stat().st_size):
        print(line)

    if args.record is not None:
        record(path, sha, args.record or None)


if __name__ == "__main__":
    main()
