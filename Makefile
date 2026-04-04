.PHONY: install run dashboard test clean

install:
	pip install -r requirements.txt

run:
	python main.py

dashboard:
	streamlit run app.py

test:
	python -m pytest tests/ -v

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +