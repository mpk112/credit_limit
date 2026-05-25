# Loan Limit Optimisation — Submission

## Contents

| File / Folder | Description |
|---|---|
| `Report_Credit_Limit_Optimisation.docx` | **Main report** — methodology, mathematical formulations, all charts, results, and answers to the five key questions |
| `loan_limit_optimization.ipynb` | Python notebook — full end-to-end implementation, runs with Restart & Run All |
| `loan_limit_increases.csv` | Input dataset (30,000 customer records) |
| `optimization_results.csv` | Output — per-customer recommended limit, increase, default risk, profitability score |
| `2025 DS Assessment.pdf` | Original assignment brief |
| `code/` | Supporting Python modules imported by the notebook |

## Running the notebook

```bash
python -m venv .venv && source .venv/bin/activate
pip install pandas numpy scipy scikit-learn pulp xgboost lightgbm matplotlib seaborn jupyter python-docx fredapi requests requests-cache

jupyter notebook loan_limit_optimization.ipynb
# Kernel → Restart & Run All
```

Macro data is pre-cached; no FRED API key needed for the baseline run.

## Key results (baseline scenario)

- **21,740 customers** (72.5%) receive a recommended limit increase
- **$16.9M** total incremental exposure (30% per-step cap; 4,932 ineligible excluded)
- **$631,741** net expected profit ($792K revenue − $160K expected losses)
- **3.51%** weighted default risk on new exposure (below 5% cap)
- **3.73%** return on incremental exposure
- **44/44** model correctness properties verified
