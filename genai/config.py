# ============================================================
# 接続設定 — この1行を書き換えるだけで切り替わります
# ============================================================
PROVIDER = "ollama"  # "ollama" または "lmstudio"

SETTINGS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "chat_model": "gemma3:4b",
        "embed_model": "bge-m3",
    },
    "lmstudio": {
        # LM Studio は「ローカルサーバー」を起動しておくこと（既定ポート 1234）
        # モデル名は LM Studio 側でロード中の名前に合わせて書き換える
        "base_url": "http://localhost:1234/v1",
        "chat_model": "google/gemma-3-4b",
        "embed_model": "text-embedding-nomic-embed-text-v1.5",
    },
}

BASE_URL = SETTINGS[PROVIDER]["base_url"]
CHAT_MODEL = SETTINGS[PROVIDER]["chat_model"]
EMBED_MODEL = SETTINGS[PROVIDER]["embed_model"]

# RAG の挙動
CHUNK_SIZE = 500      # 1チャンクの文字数（日本語は文字数ベースが扱いやすい）
CHUNK_OVERLAP = 100   # チャンク間の重なり
TOP_K = 3             # 回答に使う上位チャンク数
