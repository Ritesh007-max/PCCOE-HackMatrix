# Notebooks Directory

Interactive Jupyter exploration notebooks for research, experimentation, and exploratory data analysis (EDA).

---

## Guidelines

1. **Naming Convention**: Prefix notebooks with numeric sequences for logical progression:
   - `01_document_parsing_eda.ipynb`
   - `02_embedding_comparison.ipynb`
   - `03_retrieval_and_reranking_benchmark.ipynb`
   - `04_rule_engine_prototyping.ipynb`
2. **Clean State**: Clear all outputs before committing notebooks to keep Git diffs clean and prevent accidental exposure of sensitive tokens or data.
3. **No Production Logic**: Reusable logic developed in notebooks must be refactored into `src/` modules.
