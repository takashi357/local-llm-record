"""docs/ 内の文書をチャンク分割して埋め込み、index.json に保存する

使い方:
    python3 ingest.py
"""
import json
import pathlib
import sys

import config
import llm

DOCS_DIR = pathlib.Path(__file__).parent / "docs"
INDEX_FILE = pathlib.Path(__file__).parent / "index.json"


def split_chunks(text: str) -> list[str]:
    """文字数ベースの単純分割（重なりあり）。段落境界をなるべく尊重する。"""
    chunks = []
    step = config.CHUNK_SIZE - config.CHUNK_OVERLAP
    pos = 0
    while pos < len(text):
        chunk = text[pos:pos + config.CHUNK_SIZE]
        # チャンク末尾が段落の途中なら、直近の改行まで縮める（短くなりすぎない範囲で）
        cut = chunk.rfind("\n", int(config.CHUNK_SIZE * 0.6))
        if cut > 0 and pos + config.CHUNK_SIZE < len(text):
            chunk = chunk[:cut]
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
        pos += max(len(chunk), step) if chunk else step
    return chunks


def main() -> None:
    files = sorted(
        p for p in DOCS_DIR.glob("*")
        if p.suffix.lower() in (".txt", ".md") and p.is_file()
    )
    if not files:
        sys.exit(f"[エラー] {DOCS_DIR} に .txt / .md ファイルがありません。")

    entries = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        chunks = split_chunks(text)
        print(f"  {path.name}: {len(chunks)} チャンク")
        for chunk in chunks:
            entries.append({"source": path.name, "text": chunk})

    print(f"埋め込み中 ({config.EMBED_MODEL}, 全 {len(entries)} チャンク) ...")
    batch = 16
    for i in range(0, len(entries), batch):
        vecs = llm.embed([e["text"] for e in entries[i:i + batch]])
        for e, v in zip(entries[i:i + batch], vecs):
            e["vec"] = v
        print(f"  {min(i + batch, len(entries))}/{len(entries)}")

    INDEX_FILE.write_text(
        json.dumps({"embed_model": config.EMBED_MODEL, "entries": entries},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"完了: {INDEX_FILE.name} に保存しました。")


if __name__ == "__main__":
    main()
