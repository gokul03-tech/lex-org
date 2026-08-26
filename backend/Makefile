# LexOrch-KG backend convenience targets
.PHONY: eval eval-quick eval-corpus test lint

# Full 8-suite evaluation over the GOLD docs + HTML dashboard
eval:
	.venv/bin/python -m scripts.eval_suite --suite all --out ./reports

# Fast gate (E1+E3+E4, no retrieval/perf)
eval-quick:
	.venv/bin/python -m scripts.eval_suite --suite extraction --out ./reports && \
	.venv/bin/python -m scripts.eval_suite --suite grounding --out ./reports

# Robustness sweep across the full ./test_data corpus (checkpointed)
eval-corpus:
	.venv/bin/python -m scripts.eval_suite --suite robustness --dir ./test_data --workers 8 --out ./reports

test:
	.venv/bin/python -m pytest tests/test_eval_suite.py tests/test_batch_grounding.py -q

lint:
	.venv/bin/ruff check evals/ scripts/eval_suite.py scripts/batch_eval.py tests/test_eval_suite.py tests/test_batch_grounding.py
