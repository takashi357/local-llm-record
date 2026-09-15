# モデル受け入れ検査 — Hugging Face から現場に入れる前の関所

公開リポジトリ（Hugging Face等）から取得したモデルを、**実行せずに**検査する道具と、
配布ページで人間が確認すべきチェックリスト。閉域環境に持ち込む前の「関所」にあたる。

## なぜ要るか（2026年時点の実態）

- モデルの主流保存形式だった pickle 系（.pt / .bin 等）は、**読み込んだ瞬間に任意コードが実行され得る**。
  Hugging Face 上の悪意あるモデルによる攻撃は2024年以降繰り返し確認されている
- 検出ツール（PickleScan）自体に迂回脆弱性（CVSS 9.3 × 3件）が見つかった。
  **「スキャン済み」は安全の保証にならない**
- 2026年には、モデルの config.json に細工して `trust_remote_code=False` でも
  コードを実行させる脆弱性（transformers ライブラリ）も公表された
- 対して GGUF / safetensors は**コードを含まないデータ形式**。Ollama / LM Studio 経由の
  ローカルLLM運用はこの形式しか使わないため、pickle系のリスクをそもそも持ち込まずに済む

## 使い方

```bash
# 基本検査（形式・メタデータ・メモリ適合）
python3 modelcheck.py model.gguf

# 配布元の公表ハッシュと照合
python3 modelcheck.py model.gguf --expect-sha256 <64桁>

# 取得記録（いつ・どこから・何を）をハッシュチェーンで残す
python3 modelcheck.py model.gguf --record "https://huggingface.co/..."
```

検査内容: pickle系は開かず不合格 ／ GGUFはマジックナンバーとメタデータ
（アーキテクチャ・ライセンス・量子化・出所）を構文解析 ／ safetensorsはヘッダを検証 ／
SHA-256計算と公表値照合 ／ 実行環境のメモリに載るかの判定（1.2倍の余裕込み）。

## 配布ページで人間が確認すること（チェックリストA）

- **A-1 出所**: 発行元organizationは本物か。モデル名のタイポスクワット
  （例: `meta-11ama`）でないか。ダウンロード数・履歴が不自然でないか
- **A-2 形式**: GGUF か safetensors だけを受け入れる。.pt / .bin しか無いモデルは選び直す
- **A-3 ライセンス**: 商用利用・再配布の条件（Apache/MIT/Gemma/Llama等で全て違う）。
  委託成果物に組み込めるかは契約と突き合わせる
- **A-4 実行側の設定**: `trust_remote_code=True` は使わない。transformers を使う場合は
  最新版に保つ（config.json 経由のRCEが修正されている版か）。Ollama / LM Studio 経由なら
  この経路は元から存在しない
- **A-5 記録**: 取得URL・SHA-256・日時を `--record` で残す。閉域搬入後に
  「これは検査済みのそのファイルか」をハッシュで照合できるようにする

## 導入から定着まで（本リポジトリでの位置づけ）

1. **入口** — 本ツールで受け入れ検査（このフォルダ）
2. **配置判定** — クラウドかローカルか（fde/cloud-or-local.html）
3. **構築** — 7.6GBで動く構成（genai/）
4. **検収** — 出力照合と非送信証跡（check.py・genai/evidence.py）
5. **定着** — フルリモートFDEジョブエイド（fde/jobaid.html）の手順書・引き渡しフェーズ
