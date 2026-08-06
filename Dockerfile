FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt requirements-streamlit.txt ./
RUN pip install --no-cache-dir -r requirements-streamlit.txt
COPY . .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/_stcore/health')"
CMD ["streamlit", "run", "main.py", "--server.port=8000", "--server.address=0.0.0.0", "--server.headless=true"]
