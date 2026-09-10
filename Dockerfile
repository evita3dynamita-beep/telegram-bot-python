FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip uv==0.5.29

ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project

COPY . .

RUN uv sync --locked --no-dev --no-editable

CMD ["uv", "run", "main.py"]
