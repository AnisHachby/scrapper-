# TODO — BVC Signal vs Noise Project

Prioritized work items based on the project diagnostic. Status is tracked with `[ ]` (open) / `[x]` (done).

## 🔴 Critical — Stability & Environment

- [ ] **Install missing Python dependencies**  
  `matplotlib` and `seaborn` are listed in `requirements.txt` but not installed. Needed by `src/make_figures.py`.  
  `py -m pip install matplotlib seaborn`

- [ ] **Fix `requirements.txt` gaps**  
  The adapters and services import `httpx`, `fastapi`, `uvicorn` but they are not declared in `requirements.txt`. Add them so fresh installs work.

- [ ] **Fix git authentication for future pushes**  
  GitHub no longer accepts password auth. Configure a Personal Access Token (PAT) or use `gh auth login` so `git push` does not hang.

- [ ] **Fix data-quality errors flagged by `validate.py`**  
  - 6,364 rows (~19%) have invalid OHLC price logic (`low > high` or `close` outside `[low, high]`) in `prices_raw.parquet`.  
  - `transactions_raw.parquet` is missing — volume/block_share features will be zero.  
  - `reference_price` column is 0% complete in labeled data.

## 🟡 High — Model & Pipeline Quality

- [ ] **Improve model precision toward 70% target**  
  Current best precision is ~55% (threshold 0.75, only 29 flags). At the recommended 0.65 threshold precision is 45.14% with 14.90% recall. The `model.py` printout already warns to report this honestly as a structural finding.  
  Ideas: add more features, tune `RandomForest` hyperparameters, revisit label definitions (`ROBUSTNESS_LABEL_DEFS` in `config.py`).

- [ ] **Backfill missing raw data**  
  `data/raw/` subdirectories (`bulletins/`, `ammc/`, `dividends/`, `news/`) exist but appear empty. Run the fetch scripts to populate them:
  - `py src/fetch_bulletins.py`
  - `py src/fetch_ammc_catalysts.py`
  - `py src/fetch_news.py`
  - `py src/scrape_dividends.py`

- [ ] **Run full pipeline end-to-end in local mode**  
  `py src/run_full_pipeline.py` runs `features.py` → `labels.py` → `model.py` → `backtest.py`. Verify each step produces output in `data/processed/`.

- [ ] **Fix `validate.py` and `test_validation.py` hanging on first run**  
  Cold pandas import on Python 3.14 can be slow. Confirm tests complete and consider adding a timeout/CI step.

## 🟢 Medium — Configurability & Open Sourcing

- [ ] **Make all data sources variable / configurable**  
  See `SOURCES.md`. Move hardcoded URLs (BVC bulletins, AMMC, Boursenews, dividend calendar) into environment variables or a `sources.yaml` so the project can be reused with other exchanges.

- [ ] **Add `SOURCES.md`** (this file)  
  Documents current sources, how to override them, and open-sourcing notes.

- [ ] **Add a `CONTRIBUTING.md`**  
  Standard open-source contribution guide (bug reports, PRs, coding style).

- [ ] **Add license clarity**  
  The remote repo already contains a `LICENSE`. Confirm it matches the intended open-source license.

## 🔵 Low — Polish & Extras

- [ ] **Add CI workflow** (GitHub Actions) to run `validate.py` + `test_validation.py` on push.
- [ ] **Dockerize the monolith pipeline** (companion to the existing `services/docker-compose.yml`).
- [ ] **Document case studies** in `reports/etudes_de_cas.md` with runnable notebooks.
- [ ] **Add README usage examples** for variable sources (e.g., pointing at a different stock exchange).

---

### How to use this list
Pick one item, implement it, commit with a descriptive message, and push to `origin/main`. When an item is complete, change `[ ]` to `[x]` and push the updated `TODO.md`.