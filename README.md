# Deep Research

AIが自律的にWeb調査を行い、包括的なレポートを生成するWebアプリケーション。

## アーキテクチャ

```
┌──────────┐       ┌─────────────────────┐
│  Browser  │◄─CDN──│ Azure Static Web Apps│
│           │       │  SvelteKit SPA       │
│ localStorage      └─────────────────────┘
│ ├─チャット履歴              │
│ └─タイトル+URL   API calls + SSE
│           │                 ▼
│           │──────►┌─────────────────────────────┐
│           │       │ Azure Container Apps         │
│           │◄──SSE─│  FastAPI                     │
└──────────┘       │  ├─ TaskRegistry (in-memory) │
                    │  ├─ ResearchEngine           │──► OpenAI API (GPT-4o)
                    │  │   └─ Sources (拡張可能)    │──► Firecrawl API
                    │  └─ BlobStorageService       │
                    └──────────┬──────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Azure Blob Storage   │
                    │  調査レポート (MD)    │
                    └─────────────────────┘
```

## 技術スタック

| 層 | 技術 | Azureサービス |
|---|---|---|
| Frontend | SvelteKit (SPA / adapter-static) | Azure Static Web Apps |
| Backend | Python FastAPI | Azure Container Apps |
| LLM | OpenAI API (GPT-4o) | - |
| Web検索 / スクレイピング | Firecrawl API | - |
| 非同期処理 | asyncio Task + SSE (Server-Sent Events) | - |
| 調査結果保存 | - | Azure Blob Storage |
| チャット履歴 / タスク状態 | localStorage (フロントエンド) | - |

## 調査フロー

1. **クエリ分解** - ユーザーの質問をGPT-4oが3〜5個のサブクエリに分解
2. **Web検索** - 各サブクエリをFirecrawlで並行検索し、上位ページの本文を取得
3. **分析・深掘り判定** - 収集情報をGPT-4oが分析し、情報不足なら追加クエリを生成してステップ2へ（最大3ラウンド）
4. **レポート生成** - 全情報をもとにMarkdownレポートを生成
5. **保存** - レポートをAzure Blob Storageに保存

各ステップの進捗はSSEでリアルタイムにフロントエンドへ通知される。

## ディレクトリ構成

```
deepresearch/
├── backend/
│   ├── main.py                 # FastAPI エントリポイント + CORS
│   ├── config.py               # 環境変数 (pydantic-settings)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routers/
│   │   └── research.py         # /research エンドポイント群
│   ├── services/
│   │   ├── task_registry.py    # インメモリ タスク管理
│   │   ├── research_engine.py  # 調査オーケストレーション
│   │   └── blob_storage.py     # Azure Blob Storage 操作
│   └── sources/
│       ├── base.py             # ResearchSource 抽象基底クラス
│       ├── web_source.py       # Firecrawl Web調査
│       ├── rdb_source.py       # (将来) RDB調査
│       └── search_db_source.py # (将来) 検索DB調査
├── frontend/
│   ├── package.json
│   ├── svelte.config.js
│   └── src/
│       ├── routes/             # ページ
│       └── lib/
│           ├── api.ts          # Backend APIクライアント + SSE
│           ├── stores/         # Svelte stores (chat, research)
│           └── components/     # UI コンポーネント
├── .env.example
└── README.md
```

## APIエンドポイント

| Method | Path | 説明 |
|--------|------|------|
| POST | `/research` | 新規調査タスク作成 → `{ task_id }` |
| GET | `/research/{task_id}` | タスク状態・結果取得 |
| GET | `/research/{task_id}/stream` | SSE 進捗ストリーム |
| POST | `/research/{task_id}/cancel` | タスクキャンセル |
| GET | `/health` | ヘルスチェック |

## ローカル開発

### 環境変数

```bash
cp .env.example backend/.env
# backend/.env を編集してAPIキーを設定
```

```
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=fc-...
AZURE_STORAGE_CONNECTION_STRING=  # 空ならローカルファイル保存
AZURE_STORAGE_CONTAINER_NAME=deepresearch-results
CORS_ORIGINS=http://localhost:5173
```

### バックエンド起動

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### フロントエンド起動

```bash
cd frontend
npm install
npm run dev
```

http://localhost:5173 でアクセス。

## Azureデプロイ

| コンポーネント | サービス | 備考 |
|---|---|---|
| Frontend | Azure Static Web Apps | 無料枠あり、GitHub連携で自動デプロイ |
| Backend | Azure Container Apps | 従量課金、min=1 max=1 |
| 調査結果 | Azure Blob Storage | Hot tier、SASトークンでアクセス |

### コスト目安（1日500回利用）

- Static Web Apps: Free tier
- Container Apps: ~$10-30/月
- Blob Storage: ~$1/月以下
- **合計: ~$15-35/月**

## 設計上の特徴

- **LangChain不使用** - OpenAI SDKを直接利用したシンプルな実装
- **Source抽象化** - `ResearchSource` インターフェースにより、Web以外のデータソース（RDB、検索DB等）を追加可能
- **セマフォによる流量制御** - 100タスク同時実行でも外部APIへの同時リクエスト数を制限
- **ブラウザ非依存のタスク実行** - asyncio.Taskとして実行されるため、ブラウザを閉じても調査は継続
- **再接続対応** - ブラウザ再訪問時にlocalStorageのタスクIDからSSE再接続
