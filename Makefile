install: ; python -m pip install -r requirements.txt
pipeline: ; PYTHONPATH=src python -m readmission.pipeline
pipeline-fast: ; PYTHONPATH=src python -m readmission.pipeline --fast
app: ; streamlit run app/main.py
test: ; pytest
lint: ; ruff check .
