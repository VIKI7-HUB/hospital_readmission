install: ; pip install -r requirements.txt
pipeline: ; python -m readmission.pipeline
pipeline-fast: ; python -m readmission.pipeline --fast
app: ; streamlit run app/main.py
test: ; pytest -q -m "not slow"
lint: ; ruff check .
format: ; ruff format .
