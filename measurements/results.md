# 出力全文と生の測定値

各モデルの出力（引用部分）と Ollama の測定値をそのまま掲載しています。「文数」「所見」は私による判定です。

- 測定日: 2026-08-23
- 環境: Windows 11 / WSL 2.7.12 / Ubuntu 26.04 LTS / Ollama
- メモリ: 16.0GB（WSL 割当 7.6GB、swap 2.0GB）/ GPU: Intel Iris Xe（内蔵）

設問（全モデル共通・3回とも同一）:

```
納付書を紛失したという問い合わせに対する窓口回答を、敬語で3文以内で書いてください。
```

---

## llama3.2:3b（2.0GB）

### 1回目

> ご清聴ください。納付書を紛失した際には、速やかに状況を確認して、当事者が納付書の確認や取引内容の確認についてどう進めるかを検討するようにお勧めします。さらに、必要な手続きや取引内容の書類の再生の手続きについては、ご自身で検索もしくは専門家に相談することをお勧めします。

```
total duration:       7.34306882s
load duration:        868.088µs
prompt eval count:    57 token(s)
prompt eval duration: 638.911ms
prompt eval rate:     89.21 tokens/s
eval count:           103 token(s)
eval duration:        6.690696s
eval rate:            15.39 tokens/s
```

- 文数: 3（遵守）
- 所見: 冒頭の「ご清聴ください」が文脈に合っていません。内容も一般論にとどまり、窓口回答として機能していません。

### 2回目

> 私たちは失礼しますが、納付書を紛失したという事実は、ごみ箱などに捨てられている可能性がありますようになります。ごみ箱の確認をしてみてください。

```
total duration:       3.22668933s
load duration:        1.188507ms
prompt eval count:    57 token(s)
prompt eval duration: 68.202ms
prompt eval rate:     835.75 tokens/s
eval count:           48 token(s)
eval duration:        3.143346s
eval rate:            15.27 tokens/s
```

- 文数: 2（遵守）
- 所見: 「ありますようになります」は日本語として成立していません。内容も窓口回答になっていません。

### 3回目

> ご質問に至りましたように、弊社はご本人様の個人情報や納品書の内容などが、ご紛失になったためご迷惑をおかけしたことを sincerest apologies で表します。
>
> ご紛失を許可することで、弊社ではご本人様の納品書の内容を再発行いたしますが、ご本人様自身が再発行を必要とする場合、ご本人様は弊社の直営店や電話番号をご確認ください。
>
> ご質問などがあれば、ぜひお問い合わせください。

```
total duration:       8.797472641s
load duration:        946.041µs
prompt eval count:    57 token(s)
prompt eval duration: 67.293ms
prompt eval rate:     847.04 tokens/s
eval count:           132 token(s)
eval duration:        8.726624s
eval rate:            15.13 tokens/s
```

- 文数: 4（違反）
- 所見: 英語が混入しています（sincerest apologies）。「納付書」が「納品書」に変わっています。「弊社」「直営店」など、企業の応対で使う語彙です。

---

## gemma3:4b（3.3GB）

### 1回目

> お問い合わせありがとうございます。納付書を紛失されたとのこと、誠に恐縮いたしました。再発行の手続きにつきましては、手数料300円をご負担いただきます。詳細な手続き方法については、お電話またはメールにてお気軽にお問い合わせください。

```
total duration:       10.83259723s
load duration:        5.594977838s
prompt eval count:    35 token(s)
prompt eval duration: 1.008843s
prompt eval rate:     34.69 tokens/s
eval count:           52 token(s)
eval duration:        4.225421s
eval rate:            12.31 tokens/s
```

- 文数: 4（違反）
- 所見: **「手数料300円」は設問にない情報で、根拠がありません。** 日本語・敬語ともに自然なため、原典と照合しなければ見つけられません。

### 2回目

> お問い合わせいただきありがとうございます。納付書のご紛失につきまして、まずは状況を確認させていただきたく存じます。お手数ですが、ご本人様名、生年月日、ご住所などの情報をお伺いいただけますでしょうか。ご連絡お待ちしております。

```
total duration:       4.222424971s
load duration:        1.253865ms
prompt eval count:    35 token(s)
prompt eval duration: 222.256ms
prompt eval rate:     157.48 tokens/s
eval count:           49 token(s)
eval duration:        3.985233s
eval rate:            12.30 tokens/s
```

- 文数: 4（違反）
- 所見: 事実の誤りはありません。本人確認の情報を求める流れも妥当です。「お伺いいただけますでしょうか」は敬語としてやや不自然です（本来は「お伺いしてもよろしいでしょうか」など）。

### 3回目

> お問い合わせありがとうございます。納付書のご紛失につきまして、誠にご迷惑をおかけしており申し訳ございません。詳細を確認させていただきたいため、ご連絡先と紛失状況をお知らせいただけますでしょうか。ご協力よろしくお願いいたします。

```
total duration:       3.848352277s
load duration:        913.92µs
prompt eval count:    35 token(s)
prompt eval duration: 179.23ms
prompt eval rate:     195.28 tokens/s
eval count:           45 token(s)
eval duration:        3.650202s
eval rate:            12.33 tokens/s
```

- 文数: 4（違反）
- 所見: 事実の誤りはありません。3回の中で最も実務に近い回答です。

---

## qwen3:8b（5.2GB）

回答本文の前に、英語による推論過程が出力されます（本記録では省略しています）。

### 1回目

> ご連絡ありがとうございます。納付書の紛失についてお気の毒に思っております。お手数ですが、ご所属の窓口までお問い合わせくださいませ。ご不明点がございましたら、何卒よろしくお願いいたします。

```
total duration:       33.031268767s
load duration:        9.422678134s
prompt eval count:    37 token(s)
prompt eval duration: 1.492665s
prompt eval rate:     24.79 tokens/s
eval count:           144 token(s)
eval duration:        22.111097s
eval rate:            6.51 tokens/s
```

- 文数: 4（違反）
- 所見: 「お気の毒に思っております」は、窓口の表現として不適切です（第三者的で、当事者としての姿勢がありません）。

### 2回目

> ご連絡誠にありがとうございます。納付書の紛失に関するお手数をおかけして大変申し訳ございません。お手続きの際にご不便をおかけした点、重ねてお詫び申し上げます。お手元に残っている情報（ご納付日、金額等）をご教示いただければ、迅速に対応させていただきます。また、ご不明点がございましたら、何なりとお気軽にお問い合わせください。

```
total duration:       33.639949577s
load duration:        1.129706ms
prompt eval count:    37 token(s)
prompt eval duration: 153.171ms
prompt eval rate:     241.56 tokens/s
eval count:           200 token(s)
eval duration:        33.461718s
eval rate:            5.98 tokens/s
```

- 文数: 5（違反）
- 所見: 事実の誤りはありません。3モデル9回の中で、内容は最も適切です。ただし所要時間は33.6秒でした。

### 3回目

> ご迷惑をおかけして大変申し訳ございません。お手元に届いていない場合は、お支払いの銀行または関係部署までお問い合わせください。何卒よろしくお願い申し上げます。

```
total duration:       41.190024812s
load duration:        1.004531ms
prompt eval count:    37 token(s)
prompt eval duration: 154.036ms
prompt eval rate:     240.20 tokens/s
eval count:           236 token(s)
eval duration:        41.008187s
eval rate:            5.13 tokens/s
```

- 文数: 3（遵守）
- 所見: **案内先が誤っています。** 納付書の再発行は発行元の窓口が扱う事務であり、銀行の所管ではありません。また「お手元に届いていない場合」は紛失ではなく未着の話で、設問を取り違えています。

---

## 集計

| モデル | 容量 | 総所要（最小〜最大） | 生成速度 | 3文以内 | 事実誤りを含む回 |
|---|---|---|---|---|---|
| llama3.2:3b | 2.0GB | 3.2〜8.8s | 15.13〜15.39 tok/s | 2/3 | 日本語破綻のため評価対象外 |
| gemma3:4b | 3.3GB | 3.8〜10.8s | 12.30〜12.33 tok/s | 0/3 | 1/3（手数料300円） |
| qwen3:8b | 5.2GB | 33.0〜41.2s | 5.13〜6.51 tok/s | 1/3 | 1/3（案内先の誤り） |

9回の出力のうち、事実の誤りがなく、かつ窓口回答として成立していたのは、gemma3の2・3回目とqwen3の2回目の計3回でした。
