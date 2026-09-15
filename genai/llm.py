"""Ollama / LM Studio 共通クライアント（OpenAI互換API・標準ライブラリのみ）"""
import json
import urllib.request
import urllib.error

import config


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        config.BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise SystemExit(
            f"[エラー] {config.BASE_URL} に接続できません。\n"
            f"  PROVIDER={config.PROVIDER} のサーバーが起動しているか確認してください。\n"
            f"  詳細: {e}"
        )


def embed(texts: list[str]) -> list[list[float]]:
    """テキストのリストをベクトルのリストにする"""
    res = _post("/embeddings", {"model": config.EMBED_MODEL, "input": texts})
    data = sorted(res["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in data]


def chat(system: str, user: str) -> str:
    """1往復のチャット補完"""
    res = _post("/chat/completions", {
        "model": config.CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    })
    return res["choices"][0]["message"]["content"]
