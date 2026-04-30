# Makefile — Projet 1 : E-Commerce Olist
# Usage : make <cible>
# Sur Windows : installer make via winget (winget install GnuWin32.Make)
# ou utiliser directement les commandes Python listées ci-dessous

.PHONY: install run dashboard test clean

## Installe les dépendances
install:
	pip install -r requirements.txt

## Lance le pipeline ETL complet
run:
	python main.py

## Lance le dashboard Streamlit
dashboard:
	streamlit run app.py

## Lance les tests pytest
test:
	python -m pytest tests/ -v

## Supprime les fichiers temporaires Python
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +

## Affiche l'aide
help:
	@echo "Commandes disponibles :"
	@echo "  make install    — Installe les dépendances"
	@echo "  make run        — Lance le pipeline ETL"
	@echo "  make dashboard  — Lance le dashboard Streamlit"
	@echo "  make test       — Lance les tests pytest"
	@echo "  make clean      — Nettoie les fichiers temporaires"