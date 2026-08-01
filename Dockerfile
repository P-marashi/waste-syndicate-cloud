FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

# ---------------------------------------------------------------------
# production: frozen lockfile, no dev/test dependencies, code baked in
# ---------------------------------------------------------------------
FROM base AS production

RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "python", "run_bot.py"]

# ---------------------------------------------------------------------
# development: includes pytest/mongomock so tests can run in-container;
# code is expected to be bind-mounted over /app by docker-compose.dev.yml
# for live reload, so COPY here is just a fallback for `docker build`
# without compose.
# ---------------------------------------------------------------------
FROM base AS development

RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "python", "run_bot.py"]