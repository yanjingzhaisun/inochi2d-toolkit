# inochi2d-toolkit

[English](README.md) (canonical) · [中文](README.zh-CN.md) · **日本語**

> 英語版 README が標準の入口です。本ファイルはそれに従います。両者に差が出た場合は英語版が正しいので、
> 黙って食い違わせず pull request を送ってください。

Inochi2D のパペットを**読み取り・検証し、（段階的に）構築する**ツールキットです。人間とスクリプト向けの CLI と、エージェント向けの MCP サーバーという二つの出入口を持ちますが、どちらも同一の core に対する薄いラッパーで、黙って分岐することはありません。

Inochi2D には公式のプラグイン/IPC 口がなく、エディタ（Inochi Creator）は GUI アプリケーションです。本ツールキットは別の道を取ります。**パペット形式そのものが公開されている**——`TRNSRTS` コンテナに JSON ペイロードとテクスチャが入っている——ので、リギングはファイル層で生成・検査でき、エディタは結果を**見る**ためだけに必要になります。

## ステータス

誠実さの規約（うちの pipeline lab から引き継いだもの）：すべての機能は**実装済み / 計画中**のいずれかに分類します。未実装のものは、動くふりをせずエラーで終了します。

| 機能 | 状態 | 内容 |
| --- | --- | --- |
| `new` | 実装済み | 最小で構造的に妥当な 0.8 パペットを書き出す |
| `inspect` | 実装済み | パペットを読み、構造（ノード・パラメータ・テクスチャ）を表示。`--json`/`--tree` 対応 |
| `verify` | 実装済み | 読み → 書き → 読み の往復**に加えて**構造検証 |
| `textures` | 実装済み | 埋め込みテクスチャを抽出 |
| `from-layers` | 計画中 | レイヤー画像 → リグ済みパペット（メッシュ生成 + パラメータバインディング） |
| `render` | 計画中 | ヘッドレスで PNG にレンダリング（Creator bridge 経由） |
| `bridge` | 計画中 | ワークステーションに Creator 制御ブリッジを導入/更新 |

`inochi2d status` はコードから同じ表を出力します。

## スコープ（本リポジトリが前提とするもの・しないもの）

- **対象は Inochi2D の v0_8 ペイロード。** Live2D のパイプラインではありません。以前の 2D パペット作業から
  得た指針は再利用できますが、そのパイプラインは再利用しません。
- **既存アセットに依存しません。** 既存のモデル、リグ、レイヤーセット、3D アセットのいずれにも依存しません。
  本リポジトリを書いたワークステーションに再利用できるものはなく、手元にある 3D アセットは中間生成物であって
  **明示的に参照しません**。
- **上流の素材は未解決の依存です。** イラストはまだ制作中で、そのレイヤー分割も基準に達していません。
  したがって `from-layers` は渡されたものを信用せず、検証します。
- **人間の工程は視覚確認だけです。** PNG をレンダリングするところまでは無人で走る想定で、確認する人は
  ファイルではなく絵を見ます。

## インストール

```bash
pip install .            # core：標準ライブラリのみ
pip install '.[mcp]'     # + MCP サーバー
pip install '.[rig]'     # + numpy/Pillow（リギング関連＝計画中の機能向け）
```

## CLI

```bash
inochi2d new out.inx --name "Test Puppet"     # 最小パペット
inochi2d inspect out.inx --tree               # 構造
inochi2d verify out.inx --warnings            # 往復 + 検証、エラー時は終了コード 1
inochi2d textures out.inx --out ./textures    # テクスチャ抽出
inochi2d status                               # 機能マトリクス
```

回帰用コーパス（公式サンプル。ダウンロードするもので、コミットはしません）：

```bash
python tools/fetch_examples.py    # examples/empty08.inx (702 B), examples/ada-static.inx (7.1 MB)
pytest -q
```

## MCP

```bash
python -m inochi2d_toolkit.mcp_server          # stdio
```

ツール：`inochi_status`、`inochi_inspect`、`inochi_verify`、`inochi_extract_textures`、`inochi_new_minimal`。

MCP クライアントへの登録例（Hermes）：

```yaml
mcp_servers:
  inochi2d:
    command: /path/to/venv/bin/python
    args: [/path/to/inochi2d-toolkit/src/inochi2d_toolkit/mcp_server.py]
    enabled: true
```

## 設計

- **CLI が主体。** 機能は `src/inochi2d_toolkit/` に一度だけ実装し、二か所（`cli.py`、`mcp_server.py`）から
  公開します。MCP 層にロジックはありません。
- **core は依存ゼロ。** `inp.py` / `puppet.py` / `build.py` は標準ライブラリのみを使うので、同じコードが
  コンテナでも、Windows ワークステーションでも、MCP サーバーの中でも動きます。
- **形式がインターフェース。** バージョン整合が重要です。対象は **v0_8** ペイロード（`meta.version` = `v0.8.6`）で、
  Inochi Creator 0.8.6 に合わせています。0.9 系は変形バインディングを再構成し、新しいコンテナ（`INP2`）を
  導入しました——`docs/architecture.md` を参照。
- **信じる前に検証。** すべての書き込み経路の後に `verify` を置きます。テクスチャはバイト単位、JSON は
  ペイロードの深い等価、さらに構造チェック（uuid の一意性、mesh/uv の対応、インデックスとテクスチャ ID の範囲、
  バインディングの参照先）。

## 本ツールが依拠している形式の事実

公式サンプル二点をバイト単位で読んで確認したもの（テストで固定しています）：

```
magic        8 bytes   "TRNSRTS\0"        （本当にこの通り）
json length  uint32    ビッグエンディアン
json         N bytes   UTF-8、パペットのペイロード
"TEX_SECT"   8 bytes   必須
tex count    uint32
texture*     各：uint32 長、uint8 エンコーディング（0=PNG, 1=TGA, 2=BC7）、ペイロード
"EXT_SECT"   8 bytes   任意（ベンダー用セクション）
```

- 公式の 702 バイトのサンプルを再シリアライズすると、バイト単位で完全に一致します（`tests/test_inp.py`）。
- `Part.textures` は**固定長 3 スロットの配列**で、未使用スロットには `4294967295`（uint32 −1）が入ります。
  `meta.thumbnailId` と同じ「ここは空」を表すセンチネルで、テクスチャ ID として読んではいけません。
- `Part` は `mesh`（`verts`/`uvs` は 2 値ずつの平坦配列、`indices`、`origin`）、`blend_mode`、`tint`、
  `screenTint`、`emissionStrength`、`mask_threshold`、`opacity` を持ちます。
- 公式のテクスチャ付きサンプルのテクスチャは **TGA** です。実際には PNG だけがエンコーディングではありません。
- 公式エクスポータ自身の出力は検証で問題ゼロになります。それを指摘してしまう検証器が誤りです（これもテスト）。

## クレジット / ライセンス

MIT（`LICENSE` 参照）。選んだ理由は権限の差ではなく認知度です。MIT と BSD-2-Clause が与える権利は同じで
（使用、改変、再配布、サブライセンス、販売、クローズドソース化）、どちらもコピーレフトではないため、
本リポジトリのライセンスは上流プロジェクトに制約されません。

本ツールキットは独立したもので、Inochi2D Project とは関係ありません。上流のコードは**含みません**。
読み書きの実装は形式の挙動そのものから書き起こし、公式サンプルで検証しています。Inochi2D、Inochi Creator、
Inochi Session は Inochi2D Project による BSD-2-Clause のプロジェクトです。公式サンプルは
`tools/fetch_examples.py` がダウンロードするもので、**本リポジトリでは再配布しません**。したがって元の
ライセンスのままです。
