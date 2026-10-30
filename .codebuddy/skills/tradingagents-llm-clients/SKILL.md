---
name: tradingagents-llm-clients
description: Procedures for adding and tuning LLM providers in tradingagents/llm_clients — provider registry, model catalog, capability flags, tier resolution, and auth. This skill should be used when adding a new model or provider, fixing tool-calling or JSON/structured-output failures per provider, resolving API-key and endpoint errors, or changing the deep/quick tier split.
---

# TradingAgents LLM clients

`tradingagents/llm_clients/` turns a provider name plus a model id into a configured LangChain chat client. The graph builds exactly two clients: a **deep** thinking model and a **quick** one, each able to use a different provider and endpoint.

## Where things live

| Concern | File | Key symbols |
|---|---|---|
| Interface | `base_client.py` | `BaseLLMClient`, `normalize_content` |
| Construction | `factory.py` | `create_llm_client`, `build_llm_kwargs`, `tier_provider`, `create_tier_client` |
| Provider registry | `openai_client.py` | `OPENAI_COMPATIBLE_PROVIDERS`, `is_openai_compatible`, `check_endpoint`, `SIGNED_IN_PROVIDERS` |
| Model list for UI/validation | `model_catalog.py` | `MODEL_OPTIONS`, `_CUSTOM_ONLY`, `get_model_options`, `LEGACY_MODELS`, `get_known_models` |
| API-parameter quirks | `capabilities.py` | `ModelCapabilities`, `get_capabilities` |
| Keys / auth | `api_key_env.py`, `chatgpt_auth.py`, `waf_safety.py` | |

## `ModelCapabilities`

`supports_tool_choice`, `supports_json_mode`, `supports_json_schema`, `preferred_structured_method`, `requires_reasoning_content_roundtrip`, `requires_reasoning_split`.

Resolution order in `get_capabilities(model_name)`: exact id → regex rule → `_DEFAULT`. When a provider rejects `tool_choice` or JSON schema, the fix belongs here, not in an agent prompt.

## Do not confuse these

The root-level `models.json` in this repository is a captured `/v1/models` HTTP response with zero code references. It is **not** the model catalog and is not loaded anywhere. `model_catalog.py` (UI/validation) and `capabilities.py` (runtime API parameters) are the real sources.

## Add an OpenAI-compatible provider

1. Add a `ProviderSpec` to `OPENAI_COMPATIBLE_PROVIDERS` in `openai_client.py` — base URL, optional chat class (e.g. `DeepSeekChatOpenAI`, `MinimaxChatOpenAI`), env key.
2. Add quick and/or deep entries to `MODEL_OPTIONS` in `model_catalog.py`; add to `LEGACY_MODELS` when renaming an existing id so stored prefs still resolve.
3. Record capability overrides in `capabilities.py` if tool choice, JSON mode, or reasoning round-trips are unsupported.
4. Document the env key in `.env.example` and the README provider table.

## Add a native-protocol provider

1. `llm_clients/<provider>_client.py` implementing `BaseLLMClient.get_llm()` and `validate_model()`.
2. A branch in `factory.create_llm_client` (existing special cases: `anthropic`, `google`, `azure`, `bedrock`).
3. Catalog + capability entries.
4. Cover with `tests/test_provider_registry.py`, `tests/test_model_validation.py`.

## Tiers

`tier_provider(config, tier)` reads `quick_think_provider` / `deep_think_provider` and falls back to `llm_provider` when the tier key is `None`; `create_tier_client(config, tier, **extra)` honours `quick_think_backend_url` / `deep_think_backend_url`, falling back to `backend_url`. Model ids are `quick_think_llm` / `deep_think_llm`. The quick tier serves analysts, researchers, debaters and the trader; the deep tier serves the managers.

A provider may be quick-only without breaking deep-tier runs — say so when you register one.

## Verify

```bash
pytest -m unit tests/test_provider_registry.py tests/test_capabilities.py tests/test_model_validation.py tests/test_tier_providers.py
```

When reporting, state explicitly: provider name, model ids added, tier(s) available, and any capability downgrade callers must tolerate.

Keep this skill current: a code change here is not done until this file (and its `references/`) describe it — see *Rule — agents and skills track the code* in `AGENTS.md`.
