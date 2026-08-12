FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=0 \
    GAOKAO_HOST=0.0.0.0 \
    GAOKAO_PORT=5080

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 数据库可通过卷挂载覆盖
# docker run -v /path/to/gaokao2025.sqlite:/app/gaokao2025.sqlite ...

EXPOSE 5080

CMD ["gunicorn", "-b", "0.0.0.0:5080", "-w", "1", "--threads", "4", "--timeout", "120", "app:app"]
