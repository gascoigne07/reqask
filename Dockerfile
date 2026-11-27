# Образ агента reqask. Сборка и запуск из корня репозитория:
#   docker build --build-arg REQASK_COMMIT=$(git rev-parse --short HEAD) -t reqask .
#   docker run --rm -v "$PWD":/work reqask --input docs/requirements.md --output out/report.md
# Ключ агент берёт из файла .env в примонтированной папке, в образ ключи не попадают.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

# Коммит для паспорта отчёта: внутри образа Git нет, поэтому он передаётся при сборке.
ARG REQASK_COMMIT=""
ENV REQASK_COMMIT=${REQASK_COMMIT} PYTHONUNBUFFERED=1

WORKDIR /work
ENTRYPOINT ["reqask"]
CMD ["--help"]
