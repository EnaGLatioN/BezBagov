FROM python:3.12-slim-bookworm

WORKDIR /application
#Копируем в контейнер файл питоняшечьих зависимостей
COPY . /application
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install poetry==2.1.1
ENV PATH="/root/.local/bin:$PATH"
RUN poetry install --no-root
RUN chmod +x ./entrypoint.sh
CMD [ "./entrypoint.sh" ]