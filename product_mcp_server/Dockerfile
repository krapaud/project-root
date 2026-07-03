FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MCP_TRANSPORT=http
ENV MCP_HTTP_PORT=8100
EXPOSE 8100

CMD ["python3", "-m", "app.server"]
