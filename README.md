# Tents Database AI Manager - 統合設計・構築仕様書

本ドキュメントは、プロジェクトをゼロから完全に再現・リカバリするための設計仕様書です。AIアシスタントがスクラッチでシステムを構築、あるいは既存環境を完全に復旧させるためのすべての情報を網羅しています。

## 1. プロジェクト概要
キャンプ用テントの在庫・スペックを管理するためのインテリジェント・ダッシュボードです。
Google Gemini AIが「管理エージェント」として常駐し、Notion上の非構造化データ（メモ書き等）からスペックを抽出し、データベースを自動更新する提案を行います。

## 2. システムアーキテクチャ
- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: Vanilla HTML5 / CSS3 / JavaScript (ES6+)
- **Database**: Supabase PostgreSQL (Port: 6543 / Session Pooler)
- **AI Engine**: Google Gemini 3.1 Flash (Google GenAI SDK)
- **External Integration**: Notion API (httpxによる直接連携)

## 3. 主要機能
### 3.1 AI 管理エージェント (Dual Mode)
- **管理モード (Management)**: Notionからのデータ抽出、DB項目の修正提案、整合性チェックに特化。
- **相談モード (Assistant)**: キャンプ知識の提供、Google検索を活用した最新トレンドの調査、コーディネート提案。
- **UI提案システム**: AIはDBを直接書き換えません。`[UI_PROPOSAL: ...]` などの特殊タグを介してフロントエンドに「修正案」を送り、ユーザーが画面上で確認・編集した後に一括保存するワークフローを採用。

### 3.2 Notion 同期
- 「煩悩テント」親ページの下にある子ページをスキャンし、本文（非構造化テキスト）から「購入日」や「スペック」をAIが自動抽出します。

### 3.3 リアルタイム・エディタ
- DBから取得したデータをテーブル表示し、直接編集が可能。
- AIの提案やユーザーの手入力による変更は「未保存（赤字）」として管理され、`Validate` -> `Commit` の手順でDBへ反映。

## 4. 環境構築・セットアップ

### 4.1 前提条件
- Python 3.12 以上
- Supabase プロジェクト（PostgreSQL）
- Notion インテグレーション（トークン発行済み）
- Google Gemini API Key

### 4.2 環境変数 (.env)
セキュリティのため、具体的な接続情報やパスワードの記述は省略します。
プロジェクトの動作には、以下のキーを設定した `.env` ファイルをプロジェクトルートに配置する必要があります。
- `GEMINI_API_KEY`
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`
- `DATABASE_URL`

### 4.3 インストールと起動
```powershell
# 依存関係のインストール
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv google-generativeai httpx nest-asyncio

# サーバー起動
uvicorn main:app --reload --port 8000
```

## 5. 詳細仕様

### 5.1 データベース・スキーマ (`tents`)
| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key (Serial) |
| `name` | Text | テント名 (Not Null) |
| `brand` | Text | ブランド名 |
| `price` | Integer | 価格 (JPY) |
| `capacity` | Numeric | 定員 (e.g., 2.5) |
| `weight_kg` | Numeric | 重量 |
| `size_w/d/h` | Numeric | 使用時サイズ (cm) |
| `pack_w/d/h` | Numeric | 収納サイズ (cm) |
| `material` | Text | 素材 |
| `purchase_date` | Date | 購入日 |

### 5.2 AIツールの定義 (Function Calling)
AIは以下の関数を必要に応じて自律的に呼び出します。
- `list_tents` / `search_tents`: DB内の検索。
- `update_tent_fields`: 1件の修正案作成。
- `bulk_update_tents`: 複数件の一括修正案。
- `sync_all_from_notion`: 指定したIDのNotion情報を一括同期。
- `list_notion_tents`: Notion側のページ一覧を取得。

### 5.3 フロントエンド・ステート
- `pendingEdits`: 保存前の変更内容を保持するJSONオブジェクト。キーはテントID。
- `currentTents`: DBから取得した最新のマスターデータ。
- 表示ロジック: `currentTents` に `pendingEdits` をマージして描画。

## 6. トラブルシューティング
- **接続タイムアウト**: Supabaseのホスト名が正しいか（東京 `ap-northeast-1` か シンガポール `ap-southeast-1` か）、ポートが `6543` かを確認してください。
- **500エラー**: DBの `Decimal` 型がJSONシリアライズできない場合に発生することがあります。`schemas.py` で `from_attributes=True` を設定し、`Decimal` を適切に処理しているか確認してください。
- **文字化け**: 日本語のブランド名などが化ける場合、DBのエンコーディング（UTF-8）とクライアント側のエンコーディング設定を確認してください。
