<p align="center">
  <img src="tradingagents/assets/tauric-logo.svg" width="60%" alt="Tauric Research">
</p>

<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2412.20138" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv"/></a>
  <a href="https://discord.com/invite/hk9PGKShPK" target="_blank"><img alt="Discord" src="https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da"/></a>
  <a href="https://x.com/TauricResearch" target="_blank"><img alt="X Follow" src="https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white"/></a>
  <a href="https://github.com/TauricResearch/" target="_blank"><img alt="Community" src="https://img.shields.io/badge/GitHub_Community-TauricResearch-14C290?logo=discourse"/></a>
</div>
<br>
<div align="center">
  <a href="https://github.com/TauricResearch" target="_blank"><img alt="TradingAgents #1 Repository of the Day" src="https://trendshift.io/api/badge/repositories/16192" width="250" height="55"/></a>
</div>
<br>
<div align="center">
  <!-- Keep these links. Translations will automatically update with the README. -->
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=de">Deutsch</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=es">Español</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=fr">français</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ja">日本語</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ko">한국어</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=pt">Português</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ru">Русский</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=zh">中文</a>
</div>

---

# TradingAgents: Multi-Agents LLM Financial Trading Framework

## News

<!-- news:start -->
- [2026-10] **TradingAgents v0.7.1** released with decisions scored only on final closes and settled across long market holidays, a fix for model dates that could read filings made after the run date, and fixes to portfolios, prices, SEC statements and reports.
- [2026-10] **TradingAgents v0.7.0** released with runs on your own ChatGPT Plus or Pro plan, backtests scored from the first close after each decision, a note at start-up when a newer release is out, and a wheel attached to each GitHub release.
- [2026-10] **TradingAgents v0.6.0** released with reports saved as one HTML page, a provider per model tier so the managers and analysts can run on different models, past decisions settled for every ticker while the analysts work, and company news read from Yahoo search while Yahoo's news feed is down.

Full release notes are in [CHANGELOG.md](CHANGELOG.md).

<details>
<summary>Earlier news</summary>

- [2026-09] **TradingAgents v0.5.2** released with parallel analysts for a faster analysis, a CLI that runs without prompts from flags such as `--ticker` and `--date`, the run's settings recorded in every report, and backtests that see only data published by each analysis date.
- [2026-09] **TradingAgents v0.5.1** released with a package layout organised by what each module holds (import paths moved), optional Jev screening of social posts, GPT-6 Sol and Luna as the default models, and fixes to run isolation and SEC EDGAR statements.
- [2026-09] **TradingAgents v0.5.0** released with point-in-time integrity across every dated path, SEC EDGAR fundamentals served as filed, backtesting over a ticker and date grid, portfolio-aware runs, and current model lineups across every provider.
- [2026-08] **TradingAgents v0.4.0** released with look-ahead / point-in-time fixes across FRED macro, social sentiment, and the decision-log memory; clearer decision signals; working CLI checkpoint resume; Trader price grounding; and the GPT-5.6 and GLM-5.3 models.
- [2026-07] **TradingAgents v0.3.1** released with correctness and stability fixes: Alpha Vantage look-ahead filtering, graph-router crash-safety, graph-shape-aware checkpoint resume, working crypto sentiment sources, a configurable LLM retry budget, Bedrock API-key auth, and Claude Sonnet 5 / Fable 5 support.
- [2026-06] **TradingAgents v0.3.0** released with a verified data-access contract, an expanded provider registry (NVIDIA, Kimi, Groq, Mistral, Bedrock, and any OpenAI-compatible endpoint), FRED and Polymarket data vendors, a current-generation model catalog, and a CI gate.
- [2026-05] **TradingAgents v0.2.5** released with the grounded Sentiment Analyst, GPT-5.5 etc. model coverage, Qwen/GLM/MiniMax dual-region support, `TRADINGAGENTS_*` env-var configurability with API-key auto-detection, remote Ollama support, non-US alpha benchmarks, and ticker path-traversal hardening.
- [2026-04] **TradingAgents v0.2.4** released with structured-output agents (Research Manager, Trader, Portfolio Manager), LangGraph checkpoint resume, persistent decision log, DeepSeek/Qwen/GLM/Azure provider support, Docker, and a Windows UTF-8 encoding fix.
- [2026-03] **TradingAgents v0.2.3** released with multi-language support, GPT-5.4 family models, unified model catalog, backtesting date fidelity, and proxy support.
- [2026-03] **TradingAgents v0.2.2** released with GPT-5.4/Gemini 3.1/Claude 4.6 model coverage, five-tier rating scale, OpenAI Responses API, Anthropic effort control, and cross-platform stability.
- [2026-02] **TradingAgents v0.2.0** released with multi-provider LLM support (GPT-5.x, Gemini 3.x, Claude 4.x, Grok 4.x) and improved system architecture.
- [2026-01] **Trading-R1** [Technical Report](https://arxiv.org/abs/2509.11420) released, with [Terminal](https://github.com/TauricResearch/Trading-R1) expected to land soon.

</details>
<!-- news:end -->

<div align="center">

🚀 [TradingAgents](#tradingagents-framework) | ⚡ [Installation & CLI](#installation-and-cli) | 🖥 [Web GUI](#web-gui) | 🎬 [Demo](https://www.youtube.com/watch?v=90gr5lwjIho) | 📦 [Package Usage](#tradingagents-package) | 🤝 [Contributing](#contributing) | 📄 [Citation](#citation)

</div>

> 🎉 **TradingAgents** officially released! We have received numerous inquiries about the work, and we would like to express our thanks for the enthusiasm in our community.
>
> So we decided to fully open-source the framework. Looking forward to building impactful projects with you!

## TradingAgents Framework

TradingAgents is a multi-agent trading framework that mirrors the dynamics of real-world trading firms. By deploying specialized LLM-powered agents: from fundamental analysts, sentiment experts, and technical analysts, to trader, risk management team, the platform collaboratively evaluates market conditions and informs trading decisions. Moreover, these agents engage in dynamic discussions to pinpoint the optimal strategy.

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>

> TradingAgents framework is designed for research purposes. Trading performance may vary based on many factors, including the chosen backbone language models, model temperature, trading periods, the quality of data, and other non-deterministic factors. [It is not intended as financial, investment, or trading advice.](https://tauric.ai/disclaimer/)

Our framework decomposes complex trading tasks into specialized roles.

### Analyst Team
- Fundamentals Analyst: Evaluates company financials and performance metrics, identifying intrinsic values and potential red flags.
- Sentiment Analyst: Aggregates news headlines, StockTwits, and Reddit chatter into a single sentiment read to gauge short-term market mood.
- News Analyst: Monitors global news and macroeconomic indicators, interpreting the impact of events on market conditions.
- Technical Analyst: Utilizes technical indicators (like MACD and RSI) to detect trading patterns and forecast price movements.

The selected analysts work at the same time, each on its own tools, and the research debate starts once all of their reports are in.

<p align="center">
  <img src="assets/analyst.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

### Researcher Team
- Comprises both bullish and bearish researchers who critically assess the insights provided by the Analyst Team. Through structured debates, they balance potential gains against inherent risks.

<p align="center">
  <img src="assets/researcher.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Trader Agent
- Composes reports from the analysts and researchers to make informed trading decisions, determining the timing and magnitude of trades.

<p align="center">
  <img src="assets/trader.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Risk Management and Portfolio Manager
- Continuously evaluates portfolio risk by assessing market volatility, liquidity, and other risk factors. The risk management team evaluates and adjusts trading strategies, providing assessment reports to the Portfolio Manager for final decision.
- The Portfolio Manager approves/rejects the transaction proposal. If approved, the order will be sent to the simulated exchange and executed.

<p align="center">
  <img src="assets/risk.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

## Installation and CLI

### Installation

Clone TradingAgents:
```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

TradingAgents needs Python 3.11 or later. Create a virtual environment in any of your favorite environment managers:
```bash
conda create -n tradingagents python=3.13
conda activate tradingagents
```

Or with [uv](https://docs.astral.sh/uv/):
```bash
uv venv --python 3.13
source .venv/bin/activate
```

Install the package and its dependencies (`uv pip install .` with uv):
```bash
pip install .
```

Add `pip install ".[web]"` for the browser dashboard described under [Web GUI](#web-gui); the CLI does not need it.

### Docker

Alternatively, run with Docker:
```bash
cp .env.example .env  # add your API keys
docker compose run --rm tradingagents
```

After updating the repository, rebuild the image with `docker compose build`.

Results, reports, the memory log and the cache live in the `tradingagents_data` volume. To keep them in a folder on the host instead, create the folder and point `TRADINGAGENTS_DATA_DIR` at it, in `.env` or the shell: `mkdir -p data && TRADINGAGENTS_DATA_DIR=./data docker compose run --rm tradingagents`.

For local models with Ollama:
```bash
docker compose --profile ollama run --rm tradingagents-ollama
```

### Required APIs

TradingAgents supports multiple LLM providers. Set the API key for your chosen provider:

```bash
export OPENAI_API_KEY=...          # OpenAI (GPT)
export GOOGLE_API_KEY=...          # Google (Gemini)
export ANTHROPIC_API_KEY=...       # Anthropic (Claude)
export XAI_API_KEY=...             # xAI (Grok)
export DEEPSEEK_API_KEY=...        # DeepSeek
export DASHSCOPE_API_KEY=...       # Qwen (international, dashscope-intl.aliyuncs.com)
export DASHSCOPE_CN_API_KEY=...    # Qwen (China, dashscope.aliyuncs.com)
export ZHIPU_API_KEY=...           # GLM via Z.AI (international)
export ZHIPU_CN_API_KEY=...        # GLM via BigModel (China, open.bigmodel.cn)
export MINIMAX_API_KEY=...         # MiniMax (global, api.minimax.io)
export MINIMAX_CN_API_KEY=...      # MiniMax (China, api.minimaxi.com)
export OPENROUTER_API_KEY=...      # OpenRouter
export MISTRAL_API_KEY=...         # Mistral
export MOONSHOT_API_KEY=...        # Kimi (Moonshot)
export GROQ_API_KEY=...            # Groq
export NVIDIA_API_KEY=...          # NVIDIA NIM
export FRED_API_KEY=...            # FRED macro data (free, optional)
export ALPHA_VANTAGE_API_KEY=...   # Alpha Vantage
export TYPESAFE_API_KEY=...        # Jev social-post screening (optional)
```

For Azure OpenAI, copy `.env.enterprise.example` to `.env.enterprise` and fill in your credentials. With Docker, put these keys in `.env` instead: the image does not include `.env` files.

To run on your ChatGPT Plus or Pro plan instead of an API key, choose "Subscription" in the CLI's provider menu, or set `llm_provider: "chatgpt"`. Sign in once with `tradingagents login chatgpt`: it prints an address to open in your browser, which returns to this machine on `127.0.0.1`. When the browser runs on another machine, or TradingAgents runs in Docker (`docker compose run --rm tradingagents login chatgpt`), paste the address the browser ends up on. The sign-in is kept in `~/.tradingagents/chatgpt-auth.json`, and `tradingagents logout chatgpt` revokes it. Runs count toward your plan's usage limits, and the plan does not accept `temperature` or `max_tokens`.

For AWS Bedrock, install the extra with `pip install ".[bedrock]"`, set `llm_provider: "bedrock"`, configure AWS credentials (environment variables, `~/.aws/credentials`, or an IAM role) and `AWS_DEFAULT_REGION`, and use a Bedrock model ID, e.g. `us.anthropic.claude-opus-5-5`.

For local models, configure Ollama with `llm_provider: "ollama"`. The default endpoint is `http://localhost:11434/v1`; set `OLLAMA_BASE_URL` to point at a remote `ollama-serve`. Pull models with `ollama pull <name>`, and pick "Custom model ID" in the CLI for any model not listed by default.

For any other OpenAI-compatible server (vLLM, LM Studio, llama.cpp, or a custom relay), use `llm_provider: "openai_compatible"` and set the endpoint via `backend_url` (or `TRADINGAGENTS_LLM_BACKEND_URL`), e.g. `http://localhost:8000/v1` for vLLM or `http://localhost:1234/v1` for LM Studio. The model is whatever your server serves. No key is needed for local servers; set `OPENAI_COMPATIBLE_API_KEY` when the endpoint requires one.

With `TYPESAFE_API_KEY` set, the Sentiment Analyst screens StockTwits and Reddit posts with TypeSafe's Jev before reading them. Posts that are not about the company are dropped, and each source opens with a count of the remaining posts by stance: bullish, bearish, neutral, or unclear. Without the key, posts pass through unscreened. `jev-latest` moves with new releases; set `TYPESAFE_DEFAULT_MODEL` to a versioned ID such as `jev-1.13.0` to hold it fixed across runs. To reach Jev through OpenRouter, put an OpenRouter key in `TYPESAFE_API_KEY` and set `TYPESAFE_BASE_URL=https://openrouter.ai/api`.

Alternatively, copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### CLI Usage

Launch the interactive CLI:
```bash
tradingagents          # installed command
python -m cli.main     # alternative: run directly from source
```
You will see a screen where you can select your desired tickers, analysis date, LLM provider, research depth, and more. Your previous run's answers come back as the defaults, so pressing Enter accepts them. The `TRADINGAGENTS_*` variables in `.env` still skip their step entirely.

To run without questions, for a scheduled job or a script, answer the per-run steps with flags and the rest with `TRADINGAGENTS_*` variables:
```bash
export TRADINGAGENTS_LLM_PROVIDER=openai TRADINGAGENTS_QUICK_THINK_LLM=gpt-6-luna TRADINGAGENTS_DEEP_THINK_LLM=gpt-6-sol
export TRADINGAGENTS_OUTPUT_LANGUAGE=English TRADINGAGENTS_MAX_DEBATE_ROUNDS=1 TRADINGAGENTS_MAX_RISK_ROUNDS=1
tradingagents --ticker NVDA --date 2026-09-23 --analysts market,news,fundamentals --save --no-show
```
Each flag skips only its own question. Run without a terminal, a missing answer stops the run before it starts and names the flag or variable to set.

At start-up the interactive CLI mentions a newer release and notices from Tauric Research. It checks at most once a day, in the background, and sends nothing about your runs; set `TRADINGAGENTS_NO_UPDATE_CHECK=1` to turn it off. Runs without a terminal never check.

A saved report also includes `complete_report.html`, the report as one page with its sections listed beside the text, for reading in a browser, on a phone or in print. Answering the save question at the prompt also asks about the page and can open it in your browser; `--no-html` skips it, and so does `ta.save_reports(state, "NVDA", html=False)` from Python.

### Markets and tickers

TradingAgents takes the exchange-suffixed ticker of any market the configured vendors cover — 腾讯自选股 for A-shares, Hong Kong and US listings, Yahoo Finance for the rest — and resolves company identity and the alpha benchmark automatically per market. See [Data vendors](#data-vendors) for the default chain and how to change it.

- US: `AAPL`, `SPY`
- Hong Kong: `0700.HK` · Tokyo: `7203.T` · London: `AZN.L`
- India: `RELIANCE.NS`, `.BO` · Canada: `.TO` · Australia: `.AX`
- China A-shares: Shanghai `.SS`, Shenzhen `.SZ` (e.g. `600519.SS` for Kweichow Moutai)
- Crypto: `BTC-USD`, `ETH-USD`

<p align="center">
  <img src="assets/cli/cli_init.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

An interface will appear showing results as they load, letting you track the agent's progress as it runs.

<p align="center">
  <img src="assets/cli/cli_news.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

<p align="center">
  <img src="assets/cli/cli_transaction.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

### Web GUI

The same analysis in a browser: a React dashboard over a FastAPI backend that streams the graph's progress while it runs, instead of repainting a terminal.

#### One-key start

```bash
python scripts/start_web.py
```

Then open <http://127.0.0.1:8788>. The script does the whole sequence and stops on Ctrl+C:

1. checks the prerequisites below and refuses to guess — a missing one prints the exact command that fixes it;
2. stops with the install command if the Python `[web]` extra is missing, and runs `npm install` only when `webui/node_modules` is absent;
3. builds the dashboard (`npm run build`, i.e. `tsc --noEmit` + Vite) only when `webui/dist` is absent;
4. starts `webapi`, which serves the API and the built UI from **one** port.

| Flag | Effect |
|---|---|
| `--check` | Report every prerequisite and exit (exit code 1 if something is missing). Nothing is started. |
| `--dev` | Backend on `--port` with `--reload` plus the Vite dev server on 5173 (HMR, proxying `/api` and `/ws`) |
| `--port`, `--host` | Bind address; defaults `127.0.0.1:8788`, also settable with `TRADINGAGENTS_WEB_HOST` / `TRADINGAGENTS_WEB_PORT` |
| `--no-build` | Serve the existing `webui/dist`; fail instead of building |
| `--skip-install` | Never run `npm install` |

Check the environment without starting anything:

```bash
python scripts/start_web.py --check
#   [ok  ] python web extra (fastapi, uvicorn)
#   [ok  ] node / npm
#   [ok  ] webui/node_modules
#   [MISS] webui/dist (built UI)  ->  npm run build   (in webui/), or drop --no-build
```

#### Manual start

The script is a convenience wrapper around these commands; use them directly if you prefer:

```bash
pip install -e ".[web]"              # from the repository root — there is no pyproject.toml in webapi/
cd webui && npm install && npm run build && cd ..
python -m webapi.server              # http://127.0.0.1:8788
# or: tradingagents-web              (same entry point, console script)
```

For front-end work, run the two processes yourself instead of `--dev`:

```bash
python -m webapi.server              # terminal 1 — backend on 8788
cd webui && npm run dev              # terminal 2 — dashboard on http://localhost:5173
```

`TRADINGAGENTS_WEB_HOST` and `TRADINGAGENTS_WEB_PORT` move the backend, and the usual
`TRADINGAGENTS_*` variables still decide provider, endpoint, models, rounds and language —
the run form only asks for what changes per analysis. The built UI is served by the same
process, so one port is enough; the OpenAPI page is at `/api/docs`.

| What | Where | Notes |
|---|---|---|
| Dashboard + API | `127.0.0.1:8788` | Single-port mode; `webui/dist` is served by `webapi` |
| Dashboard (dev) | `localhost:5173` | Vite; proxies `/api` and `/ws` to the backend port |
| API docs | `127.0.0.1:8788/api/docs` | OpenAPI, always available |
| Health | `127.0.0.1:8788/api/health` | `{ok, version, busy}` — `busy` is true while a run is queued or running |
| Logs | `~/.tradingagents/logs/web/` | See [Logs](#logs) |

Development notes for each half — module layout, endpoints, threading, event flow, build
output: [`webapi/README.md`](webapi/README.md) and [`webui/README.md`](webui/README.md).

| Panel | What it shows |
|---|---|
| Agent pipeline | The five teams (analysts, research, trader, risk, portfolio) with each agent's status, the completed count and what is being written right now |
| Live activity | Messages and tool calls as they arrive, interleaved in one timeline, filterable by type; long entries collapse |
| Reports | One tab per report section, filled in as each agent files it, with the unfiled ones naming the agent still working |
| Portfolio Manager decision | The rating, its headline fields (`Price target`, `Time horizon`, …) and the decision text |
| Stats bar | Elapsed time, LLM calls, tool calls, tokens in/out, agents and reports done, and whether the stream is live |
| Runs / History | The runs of this session, and every decision already recorded on disk for that ticker and date |

Everything the terminal view derives is derived here the same way: an analyst is `in_progress` until its own report lands, the research team starts when all selected analysts have filed, and the risk debate follows the trader's plan. `Cancel` stops the run after the current step; reports, the state log and the memory log are still written for a run that completes.

One analysis runs at a time: `TradingAgentsGraph` installs its config process-wide, so a second request queues behind the first rather than reading another run's settings. The queue depth shows in the run's status.

| Endpoint | Purpose |
|---|---|
| `GET /api/config` | The effective provider, endpoint, models, rounds, language and paths (never keys) |
| `GET /api/runs`, `GET /api/runs/{id}` | Run list and one run's full snapshot |
| `POST /api/runs` | Start a run: `ticker`, `analysis_date`, `analysts`, `asset_type`, and optional model/round/language overrides |
| `POST /api/runs/{id}/cancel`, `DELETE /api/runs/{id}` | Ask a run to stop, or drop it from memory |
| `GET /api/history`, `GET /api/history/{ticker}/{date}` | Decisions already recorded under `results_dir`, newest first |
| `WS /ws/runs/{id}` | A full snapshot on connect, then `status`, `agents`, `message`, `tool_call`, `report`, `stats`, `decision` and `error` deltas |

Live runs are held in the process's memory, so restarting the server forgets them — the files under `results_dir` do not, and the History tab reads those back.

#### Logs

The web service writes rotating logs, one file per level, into `{results_dir}/web` (`~/.tradingagents/logs/web` by default):

| File | Holds |
|---|---|
| `trace.log` | Everything, i.e. TRACE and up |
| `debug.log` | DEBUG and up: graph construction, checkpoint thread, tool calls, report sizes |
| `info.log` | INFO and up: run created, status changes, agent completions, the rating, HTTP requests, WebSocket connects |
| `error.log` | ERROR and up: failed runs with their traceback |

TRACE is a level of our own, below DEBUG: every message, every streamed chunk with its state keys, every event delivered to a browser, and every status transition. That is the level that explains a run which stalls rather than fails, so it sits behind its own switch — a normal run writes thousands of these lines.

Switches, in `.env` (a blank value means "unset" and keeps the default):

```bash
TRADINGAGENTS_LOG_ENABLED=1        # every file handler; 0 turns logging off
TRADINGAGENTS_LOG_DIR=             # unset: {results_dir}/web
TRADINGAGENTS_LOG_TRACE=0          # trace.log (TRACE and up); off by default
TRADINGAGENTS_LOG_DEBUG=1          # debug.log
TRADINGAGENTS_LOG_INFO=1           # info.log
TRADINGAGENTS_LOG_ERROR=1          # error.log
TRADINGAGENTS_LOG_LEVEL=info       # console level: trace|debug|info|warning|error
TRADINGAGENTS_LOG_CONSOLE=1        # echo to stderr alongside the files
TRADINGAGENTS_LOG_PAYLOADS=0       # include message and report bodies at TRACE
TRADINGAGENTS_LOG_MAX_BYTES=10485760
TRADINGAGENTS_LOG_BACKUPS=5        # rotated files kept per level
TRADINGAGENTS_LOG_LIBRARIES=0      # let httpx/langchain/uvicorn log at their own level
```

`PAYLOADS=1` puts the text itself in `trace.log` — analyst messages, report bodies, tool arguments — which is what you want when reproducing a bad decision, and is why it is off by default. `LIBRARIES=1` releases the clamp that holds third-party loggers at WARNING; uvicorn's per-socket protocol trace is the reason that clamp exists.

Each line carries the time, level, logger and thread, and run work is named after its run, so one analysis can be pulled out with a filter:

```bash
grep "run=3f2a1c9b8d4e" ~/.tradingagents/logs/web/info.log
```

#### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `does not appear to be a Python project: neither 'setup.py' nor 'pyproject.toml' found` | `pip install -e ".[web]"` was run inside `webapi/` or `webui/`. Go to the repository root, or use `pip install -e "..[web]"` in place. |
| Browser gets a JSON 404 at `/` (or "UI build not found.") | `webui/dist` is missing. `python scripts/start_web.py` builds it; or `npm run build` in `webui/`. The API keeps working either way. |
| `Address already in use` on 8788 | Another server holds the port: `python scripts/start_web.py --port 8899`, or stop the other one. |
| `npm` not found | Node 18+ is needed only to build or hot-reload the dashboard; with a built `dist` the API serves it without Node. |
| A run sits at `Queued` and never starts | Only one analysis runs at a time. `/api/health` reports `busy`; the run starts when the current one finishes. |
| WebSocket closes with code `4404` | The server restarted and no longer holds that run in memory — live runs are process-local. The History tab still reads what was written to `results_dir`. |
| `pytest -m unit` is green but the dashboard tests never ran | `tests/test_webapi_*.py` carry no `pytestmark`, so `-m unit` deselects them. Name the files explicitly. |

### Data vendors

Every price read — the analyst's CSV, the indicators, the verified snapshot, and the closes a decision is settled against — comes from one chain of vendors, chosen per category. The defaults need no key and no configuration:

| Category | Default | Serves |
|---|---|---|
| `core_stock_apis` | `tencent,yfinance` | Every price read |
| `technical_indicators` | `local` | Computed from those prices, no indicator API |
| `fundamental_data` | `sec_edgar,yfinance` | Statements as filed, then Yahoo |
| `news_data` | `yfinance` | Ticker and market news |
| `macro_data` | `fred` | FRED series (needs `FRED_API_KEY`) |
| `prediction_markets` | `polymarket` | Market-implied probabilities |

A category is an ordered chain, tried in order. `tencent` (腾讯自选股, no key: A-shares, Hong Kong and US listings, plus a few indices) leads because Yahoo's API is withdrawn from some networks; `yfinance` follows it for the symbols Tencent does not quote — futures, FX, crypto, other regions. A vendor that fails in transit, or does not quote the symbol, hands the read to the next one.

Set the chain in `.env` as JSON. Categories you leave out keep their defaults:

```bash
# Tencent first, Yahoo behind it — the default, written out
TRADINGAGENTS_DATA_VENDORS={"core_stock_apis":"tencent,yfinance"}

# Tencent only: never touch Yahoo, at the cost of every symbol Tencent does not quote
TRADINGAGENTS_DATA_VENDORS={"core_stock_apis":"tencent"}

# Chinese-language news from 东方财富 (no key) alongside Tencent prices
TRADINGAGENTS_DATA_VENDORS={"core_stock_apis":"tencent","news_data":"eastmoney"}
```

A leading `export`, a single-quoted value, and the nested shape are all accepted. The nested shape is what a tool-level override needs, since `get_insider_transactions` lives in `news_data`, which 东方财富 does not serve:

```bash
TRADINGAGENTS_DATA_VENDORS={"data_vendors":{"core_stock_apis":"tencent","news_data":"eastmoney"},"tool_vendors":{"get_insider_transactions":"yfinance"}}
```

`.env` is found from the working directory upward, so start TradingAgents from the directory that holds it. Check what a run will use with:

```bash
python -c "from tradingagents.default_config import DEFAULT_CONFIG as c; print(c['data_vendors'])"
```

Naming one vendor is not the same as listing a chain: `{"core_stock_apis":"tencent"}` reports `NO_DATA_AVAILABLE` for a symbol Tencent does not quote, where the default chain falls through to Yahoo. Yahoo answering with its "services are no longer accessible" page is reported as a network block and is not retried — no retry turns a 403 page into data; name another vendor, or route the request through a proxy.

## TradingAgents Package

### Implementation Details

We built TradingAgents with LangGraph to ensure flexibility and modularity. The framework supports multiple LLM providers: OpenAI, Google, Anthropic, xAI, DeepSeek, Qwen (Alibaba DashScope, international and China endpoints), GLM (Zhipu), MiniMax (global + China), OpenRouter, Ollama for local models, Azure OpenAI for enterprise, and your own ChatGPT plan.

### Python Usage

To use TradingAgents inside your code, you can import the `tradingagents` module and initialize a `TradingAgentsGraph()` object. The `.propagate()` function will return a decision. You can run `main.py`, here's also a quick example:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())

# forward propagate
state, decision = ta.propagate("NVDA", "2026-09-01")
print(decision)

# the same report tree the CLI saves, under results_dir/reports
ta.save_reports(state, "NVDA")
```

You can also adjust the default configuration to set your own choice of LLMs, debate rounds, etc.

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"        # e.g. openai, google, anthropic, deepseek, groq, ollama; openai_compatible covers any OpenAI-compatible endpoint (vLLM, LM Studio, llama.cpp, ...)
config["deep_think_llm"] = "gpt-6-sol"    # Model for complex reasoning
config["quick_think_llm"] = "gpt-6-luna"   # Model for quick tasks
config["max_debate_rounds"] = 2

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2026-09-01")
print(decision)
```

The quick model serves the analysts, researchers, debaters and trader; the deep model serves the research and portfolio managers. Each can run on its own provider, for example the managers on Claude while the rest run on OpenAI:

```python
config["deep_think_provider"] = "anthropic"
config["deep_think_llm"] = "claude-opus-5-5"
```

A tier on its own provider uses that provider's key and default endpoint; set `quick_think_backend_url` or `deep_think_backend_url` for a local or relay endpoint. The `TRADINGAGENTS_DEEP_THINK_PROVIDER` and `TRADINGAGENTS_QUICK_THINK_PROVIDER` variables set them for the CLI, together with the tier's model variable.

See `tradingagents/default_config.py` for all configuration options.

### Fundamentals as filed

US company statements come from SEC EDGAR, which records the date every figure was filed. A run dated in the past reads the statements exactly as they stood that day: a fiscal year that has ended but has not been filed yet is not served, and a figure restated later still reads as first reported. Apple's 2008 total assets were filed as $39.6B and restated to $36.2B in 2010, so a run dated in between reads $39.6B. EDGAR needs no account or API key.

Other companies' statements come from Yahoo Finance, which dates a statement by the period it covers rather than by when it was published. A run dated today reads them; a run dated in the past is told they are withheld, since Yahoo cannot say which figures were public by then.

Insider trades are dated by when they happened, not when they were filed, so a run dated in the past is told they are withheld as well.

SEC asks callers to identify themselves and refuses requests that carry no contact address, so a default one is sent. Set your own so SEC can reach you rather than the project:

```bash
SEC_EDGAR_USER_AGENT="Your Name your@email.com"
```

It covers companies that file with the SEC, including foreign companies listed in the US. Anything else, such as Hong Kong or A-share listings, falls through to the next vendor in the chain. EDGAR's machine-readable filings begin in 2009, and a fourth quarter is reported as unavailable rather than derived, because filers publish it only inside the annual figure.

### Current holdings

By default the agents do not know what you hold, so their guidance is written for a reader who applies it to their own position. Pass a portfolio to have the trader, the risk analysts and the portfolio manager work against your actual book.

```python
from tradingagents.portfolio import PortfolioContext

portfolio = PortfolioContext.model_validate({
    "cash": 25000.0,
    "currency": "USD",
    "positions": [{"ticker": "NVDA", "quantity": 120, "average_price": 150.0}],
})
_, decision = ta.propagate("NVDA", "2026-09-01", portfolio=portfolio)
```

The CLI takes the same content as a JSON file: `tradingagents --portfolio my_book.json`.

An empty `positions` list means a flat book, which is different from passing nothing. A run without a portfolio is never treated as flat.

## Persistence and Recovery

TradingAgents persists two kinds of state across runs.

### Memory log

The memory log is always on. Each completed run appends its decision to `~/.tradingagents/memory/trading_memory.md`. While the analysts of a later run work, TradingAgents settles every logged decision whose holding period has passed: it fetches the realised return (raw, and alpha against the instrument's regional benchmark) and generates a one-paragraph reflection. The Portfolio Manager then reads the most recent decisions for the same ticker plus recent lessons from other tickers, so each analysis carries forward what worked and what didn't. If settling fails, the run goes on and its report says so.

Override the path with `TRADINGAGENTS_MEMORY_LOG_PATH`.

To settle decisions without running an analysis, for a scheduled job, call `ta.settle_all_pending()`; it returns the decisions it settled and any it could not.

### Checkpoint resume

Checkpoint resume is opt-in via `--checkpoint`. When enabled, LangGraph saves state after each node so a crashed or interrupted run resumes from the last successful step instead of starting over. The run view says whether it resumed a saved run or started fresh. Checkpoints are cleared automatically on successful completion.

Per-ticker SQLite databases live at `~/.tradingagents/cache/checkpoints/<TICKER>.db` (override the base with `TRADINGAGENTS_CACHE_DIR`). Use `--clear-checkpoints` to reset all of them before a run.

```bash
tradingagents --checkpoint           # enable for this run
tradingagents --clear-checkpoints    # reset before running
```

```python
config = DEFAULT_CONFIG.copy()
config["checkpoint_enabled"] = True
ta = TradingAgentsGraph(config=config)
_, decision = ta.propagate("NVDA", "2026-09-01")
```

## Evaluating decisions over time

One run gives one decision, which cannot tell you whether the system decides well. `run_backtest` runs the same pipeline over a grid of tickers and dates, writes to a memory log of its own, and scores the decisions whose holding window has since traded.

```python
from tradingagents.backtest import iter_grid, run_backtest, summarize

dates = iter_grid("2026-06-01", "2026-08-01", every_n_days=7)
result = run_backtest(["NVDA", "AAPL"], dates, config, selected_analysts=["market", "news"])
print(summarize(result).render())
```

From the CLI:

```bash
tradingagents backtest NVDA,AAPL --start 2026-06-01 --end 2026-08-01 --every 7
```

Each cell is scored on realized alpha against the instrument's regional benchmark, grouped by rating. A decision is entered at the first close after its date, because a run reads news published after that day's close. Your own memory log is never written to, and re-running the same grid with `run_id=result.run_id` skips the cells that already ran, so an interrupted sweep continues where it stopped.

## Reproducibility

TradingAgents is LLM-driven, so two runs of the same ticker and date can differ. This is expected for a research tool built on language models, not a defect. The variation comes from a few distinct sources, and it helps to separate them.

Language model sampling is non-deterministic. Even at a fixed temperature, providers do not guarantee byte-identical output across calls, and reasoning models (the default GPT-6 family, and any thinking-mode model) vary the most because their internal reasoning is itself sampled.

Live data moves. News, StockTwits, and Reddit return different content as time passes, so a run today sees different inputs than a run last week even for the same historical trade date. Pin the analysis date to hold the price and indicator window fixed, but the social and news sources still reflect "now".

To reduce variation you can lower the sampling temperature. Set `temperature` in your config (or `TRADINGAGENTS_TEMPERATURE` in `.env`); lower values make models that honor it more repeatable. The current curated models are reasoning-first and largely ignore temperature, so for tighter reproducibility name a non-reasoning model in your config, or in `TRADINGAGENTS_DEEP_THINK_LLM` and `TRADINGAGENTS_QUICK_THINK_LLM`. Any model ID your provider serves is accepted, whether or not the picker lists it.

```python
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["temperature"] = 0.0
# Reasoning models ignore temperature. For tighter reproducibility, name a
# non-reasoning model in deep_think_llm / quick_think_llm.
```

What does not vary anymore: the analyzed company identity is resolved deterministically from the ticker before any agent runs, and the market analyst grounds exact price and indicator claims in a verified data snapshot. Earlier reports of "different companies" or fabricated price levels across runs are addressed by these two mechanisms.

Backtest results are not guaranteed to match any published figure. Returns depend on the model, the temperature, the date range, data quality, and the sampling above. Treat the framework as a research scaffold for studying multi-agent analysis, not as a strategy with a fixed, replicable return.

## Contributing

Contributions are welcome: bug fixes, documentation, and feature ideas; past contributions are credited per release in [`CHANGELOG.md`](CHANGELOG.md).

## Citation

Please reference our work if you find *TradingAgents* provides you with some help :)

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
```
