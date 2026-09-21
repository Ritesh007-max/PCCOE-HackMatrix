# Models Directory

Local model weight storage and local artifact cache.

> **Note**: Binary model weights, checkpoints, and safetensors files are strictly excluded from Git tracking via `.gitignore`. Download or fine-tune models through provided automation scripts.

---

## Subdirectories

- `embeddings/`: Local dense vector embedding weights (e.g., SentenceTransformers, HuggingFace weights).
- `reranker/`: Local cross-encoder re-ranking models (e.g., BAAI/bge-reranker, ms-marco-MiniLM).
- `classifiers/`: Lightweight classification models (intent detection, policy domain routing).
- `checkpoints/`: Training/fine-tuning model checkpoints and state dicts.
