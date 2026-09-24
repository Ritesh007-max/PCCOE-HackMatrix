# Evaluation Metrics Framework (`src/evaluation/metrics.py`)

## 1. Quantitative Metric Formulations

### Retrieval Metrics:
- **Hit@K**: $\text{Hit@K} = 1.0 \text{ if } \text{target} \in \text{retrieved}[:K] \text{ else } 0.0$
- **MRR (Mean Reciprocal Rank)**: $\text{MRR} = \frac{1}{\text{rank}}$ where rank is the 1-indexed position of the target scheme.
- **Precision@K**: $\text{Precision@K} = \frac{|\text{retrieved}[:K] \cap \text{relevant}|}{K}$
- **Recall@K**: $\text{Recall@K} = \frac{|\text{retrieved}[:K] \cap \text{relevant}|}{|\text{relevant}|}$

### Extraction Metrics:
- **Precision**: $\text{Precision} = \frac{\text{correct\_fields}}{\text{extracted\_fields}}$
- **Recall**: $\text{Recall} = \frac{\text{correct\_fields}}{\text{expected\_fields}}$
- **F1 Score**: $F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$

### Decision & Statutory Metrics:
- **PASS Accuracy**: Fraction of eligible profiles correctly outputting `PASS`.
- **FAIL Accuracy**: Fraction of ineligible profiles correctly outputting `FAIL`.
- **UNKNOWN Accuracy**: Fraction of incomplete profiles correctly outputting `UNKNOWN` (Target: 1.00).
- **REVIEW Accuracy**: Fraction of conflicting profiles correctly outputting `REVIEW` (Target: 1.00).

### Security & Red Team Metrics:
- **Injection Block Rate**: Fraction of prompt injection attacks intercepted or rendered ineffective.
- **Gate Enforcement Rate**: Fraction of poisoned policy candidate datasets blocked by activation gates.
- **Secret Leakage Count**: Absolute count of API keys, passwords, or PII detected in error responses (Target: 0).
- **Unauthorized State Mutation**: Count of unauthorized state changes (Target: 0).
