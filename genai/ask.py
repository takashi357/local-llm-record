"""index.json を検索し、根拠付きで質問に回答する

使い方:
    python3 ask.py "質問文"
    python3 ask.py --show "質問文"   # 参照したチャンク本文も表示
"""
import json
import math
import pathlib
import sys

import config
import evidence
import llm

INDEX_FILE = pathlib.Path(__file__).parent / "index.json"

# gemma などの小型モデルは system ロールの指示を軽視しがちなので、
# 指示は user メッセージ側にまとめる
PROMPT_TEMPLATE = """次の参考資料を読んで、最後の質問に日本語で簡潔に答えてください。
回答は参考資料に書かれている内容だけを根拠にし、根拠となる条文や箇所があれば挙げてください。
参考資料をよく探しても答えが見つからない場合のみ「資料には記載がありません」と答えてください。

# 参考資料
{context}

# 質問
{question}"""


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def load_index() -> dict:
    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            "index.json がありません。先に python3 ingest.py を実行してください。")
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    if index["embed_model"] != config.EMBED_MODEL:
        raise RuntimeError(
            f"index.json は {index['embed_model']} で作成されています。"
            f"現在の設定 ({config.EMBED_MODEL}) で ingest.py を再実行してください。")
    return index


def answer(question: str) -> dict:
    """検索→生成→証跡記録までを行い、結果を辞書で返す"""
    index = load_index()
    qvec = llm.embed([question])[0]
    scored = sorted(
        index["entries"],
        key=lambda e: cosine(qvec, e["vec"]),
        reverse=True,
    )[:config.TOP_K]

    context = "\n\n".join(
        f"【資料{i + 1}: {e['source']}】\n{e['text']}" for i, e in enumerate(scored)
    )
    text = llm.chat(
        "あなたは社内文書に基づいて正確に回答するアシスタントです。",
        PROMPT_TEMPLATE.format(context=context, question=question),
    ).strip()
    record = evidence.append_record(question, text)
    return {
        "answer": text,
        "sources": list(dict.fromkeys(e["source"] for e in scored)),
        "context": context,
        "offline": record["network"]["offline"],
        "timestamp": record["timestamp"],
    }


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--show"]
    show = "--show" in sys.argv
    if not args:
        sys.exit('使い方: python3 ask.py "質問文"')

    try:
        result = answer(args[0])
    except (FileNotFoundError, RuntimeError) as e:
        sys.exit(f"[エラー] {e}")

    if show:
        print("=== 参照チャンク ===")
        print(result["context"])
        print("====================\n")
    print(result["answer"])
    print("\n--- 参照元:", ", ".join(result["sources"]))
    state = "オフライン実行" if result["offline"] else "オンライン実行"
    print(f"--- 証跡: evidence.jsonl に記録（{state} / {result['timestamp']}）")


if __name__ == "__main__":
    main()
