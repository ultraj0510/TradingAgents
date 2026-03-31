# TradingAgents 日本株対応 設計ドキュメント

**日付**: 2026-03-31
**ステータス**: 承認済み

---

## 概要

TradingAgents を日本株（JPX/TSE 上場銘柄）に対応させる。既存の US 株ロジックはそのまま維持し、`.T` サフィックス（例: `7203.T`）を検出して Japan プロファイルを自動選択する。データ取得は yfinance を最大限活用し、不足する日本語ニュースのみ RSS で補完する。

---

## 要件

| 項目 | 内容 |
|------|------|
| 株価・テクニカル | yfinance をそのまま活用（変更なし） |
| ファンダメンタルズ | yfinance をそのまま活用（JPY 建てで自動取得） |
| 日本語ニュース | RSS フィード（無料）を新ベンダーとして追加 |
| 市場カレンダー | JPX 祝日・休業日を `jpholiday` ライブラリで完全対応 |
| 出力言語 | 設定で選択可能（`auto` 時は市場プロファイルから推定） |

---

## アーキテクチャ

```
ticker 入力（例: 7203.T）
    ↓
market_profile.py  ← ".T" 検出 → "japan"
    ↓
dataflows/
  y_finance.py          ← 変更なし（株価・テクニカル・ファンダメンタルズ）
  news_japan_rss.py     ← 新規追加（RSS ニュース）
  market_calendar.py    ← 新規追加（JPX 祝日判定）
  market_profile.py     ← 新規追加（市場判定・プロファイル管理）
  interface.py          ← 軽微な修正（新ベンダー登録）
    ↓
agents/utils/agent_utils.py  ← 市場コンテキスト注入を拡張
    ↓
出力（output_language 設定に従い日本語 or 英語）
```

---

## コンポーネント詳細

### 1. `tradingagents/dataflows/market_profile.py`（新規）

市場プロファイルの判定と管理。

```python
def detect_market(ticker: str) -> str:
    """".T" サフィックスで "japan" を返す。それ以外は "us"。"""

def get_profile(market: str) -> MarketProfile:
    """MarketProfile(currency, language_default, calendar, exchange_tz) を返す。"""
```

`MarketProfile` は dataclass で定義。Japan プロファイルの値：
- `currency`: "JPY"
- `language_default`: "japanese"
- `exchange_tz`: "Asia/Tokyo"
- `trading_hours`: {"open": "09:00", "close": "15:30"}

---

### 2. `tradingagents/dataflows/market_calendar.py`（新規）

JPX の取引日管理。`jpholiday` ライブラリを使用。

```python
def is_trading_day(date: datetime.date, market: str) -> bool:
    """土日・祝日・年末年始を除いた取引日かどうかを返す。"""

def last_trading_day(date: datetime.date, market: str) -> datetime.date:
    """指定日以前の直近取引日を返す（分析対象日の補正に使用）。"""
```

`jpholiday` 未インストール時は祝日チェックをスキップしてワーニングを出力する。

---

### 3. `tradingagents/dataflows/news_japan_rss.py`（新規）

日本語 RSS ニュースの取得。

対象 RSS ソース（初期実装）：
- Yahoo Finance Japan: `https://finance.yahoo.co.jp/rss/stocks/{code}.xml`
- NHK ニュース（経済）: `https://www3.nhk.or.jp/rss/news/cat5.xml`

処理フロー：
1. ティッカー（`7203.T`）→ 銘柄コード（`7203`）と会社名を取得
2. 対象 RSS を取得・パース（`feedparser` ライブラリ使用）
3. 会社名・銘柄コードでフィルタリング
4. 既存の `yfinance_news.py` と同じ形式のリストを返す

RSS 取得失敗時は yfinance の英語ニュースにフォールバックする。

---

### 4. `tradingagents/dataflows/interface.py`（修正）

軽微な修正のみ：
- `TOOLS_CATEGORIES` に `"news_japan_rss"` ベンダーを追加
- Japan プロファイル検出時に `news_data` カテゴリのデフォルトベンダーを `"news_japan_rss"` に切り替え

---

### 5. `tradingagents/default_config.py`（修正）

設定項目を追加：

```python
"market": "auto",           # "auto" | "japan" | "us"
"output_language": "auto",  # "auto" | "japanese" | "english"
```

`"auto"` の場合、`market_profile.detect_market(ticker)` の結果を使用する。

---

### 6. `tradingagents/agents/utils/agent_utils.py`（修正）

`build_instrument_context()` に市場プロファイルを渡し、以下を全エージェントに注入：

- **通貨コンテキスト**: "価格は円（JPY）建てで解釈してください"
- **取引慣行**: "日本株は通常 100 株単位（単元株）で取引されます"
- **出力言語指示**: `output_language` 設定に従い日本語または英語で回答するよう指示

各エージェントのプロンプトファイルは変更しない。

---

## 依存ライブラリの追加

`pyproject.toml` に以下を追加：

```toml
"jpholiday",    # JPX 祝日判定
"feedparser",   # RSS パース
```

---

## テスト方針

既存テスト (`tests/`) は変更しない。新規テストファイルを追加：

**`tests/test_japan_market.py`**:
- `detect_market("7203.T")` → `"japan"` であること
- `detect_market("AAPL")` → `"us"` であること
- `is_trading_day(土曜日)` → `False` であること
- `is_trading_day(祝日)` → `False` であること
- `last_trading_day(祝日)` → 直前の平日を返すこと
- RSS ニュース取得が失敗したとき yfinance ニュースにフォールバックすること

---

## エラーハンドリング

| ケース | 対応 |
|--------|------|
| RSS 取得失敗 | yfinance 英語ニュースにフォールバック、ログ出力 |
| `jpholiday` 未インストール | 祝日チェックスキップ + WARNING ログ |
| 不明なティッカー形式 | `"us"` プロファイルをデフォルトとして使用 |

---

## 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|----------|----------|------|
| `tradingagents/dataflows/market_profile.py` | 新規 | 市場判定・プロファイル管理 |
| `tradingagents/dataflows/market_calendar.py` | 新規 | JPX カレンダー |
| `tradingagents/dataflows/news_japan_rss.py` | 新規 | RSS ニュース取得 |
| `tradingagents/dataflows/interface.py` | 修正 | 新ベンダー登録 |
| `tradingagents/default_config.py` | 修正 | market / output_language 設定追加 |
| `tradingagents/agents/utils/agent_utils.py` | 修正 | 日本市場コンテキスト注入 |
| `pyproject.toml` | 修正 | jpholiday / feedparser 追加 |
| `tests/test_japan_market.py` | 新規 | 日本株対応テスト |

---

## 非対象（スコープ外）

- Alpha Vantage の日本株対応（yfinance で代替）
- TDnet・EDINET 等の IR データ統合
- 日本語センチメント分析モデルの特別チューニング
- バックテストの市場カレンダー対応（将来課題）
