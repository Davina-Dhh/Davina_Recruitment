FROM python:3.11-slim

WORKDIR /app

# 需要 Hiring-Radar 仓库根目录作为构建上下文：
#   docker build -f dashboard/Dockerfile -t davina-qiuzhao .
COPY parsers /app/parsers
COPY hiring_radar.py /app/hiring_radar.py
COPY dashboard /app/dashboard

WORKDIR /app/dashboard
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

EXPOSE 8501

CMD ["streamlit", "run", "davina_workbench.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.headless", "true"]
