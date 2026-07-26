#!/bin/sh
streamlit run main.py --server.port "${PORT:-8000}" --server.address 0.0.0.0 --server.headless true
