#!/bin/bash
set -e

# Вывод переданных переменных окружения
echo "Переданные переменные окружения:"
env | grep -E '^[A-Z0-9_]+' || echo "Нет переменных."

# Массив команд, которые нужно запустить
COMMANDS=(
    "poetry run python bez_bagov/manage.py migrate"
    "poetry run python bez_bagov/manage.py runserver 0.0.0.0:8000"
)

# Функция обработки завершения контейнера
terminate() {
    echo "Остановка контейнера..."

    # Отправляем SIGTERM всем процессам
    for pid in "${PIDS[@]}"; do
        echo "Завершаем процесс PID=$pid..."
        kill -TERM "$pid" 2>/dev/null || true
    done

    # Ждём завершения всех процессов перед выходом
    wait
    echo "Все процессы завершены."
    exit 0
}

# Обрабатываем сигналы SIGTERM и SIGINT (например, при `docker stop`)
trap terminate SIGTERM SIGINT

# Массив для хранения PID запущенных процессов
declare -a PIDS

# Запускаем все процессы
for ((i = 0; i < ${#COMMANDS[@]}; i++)); do
    cmd="${COMMANDS[i]}"

    if [[ $i -eq 0 ]]; then
        # Главный процесс (он остаётся в foreground и логируется в `docker logs`)
        echo "Запускаю (выводит логи в docker logs): $cmd"
        eval "$cmd" &
    else
        # Все остальные процессы запускаются в фоне
        echo "Запускаю (в фоне): $cmd"
        eval "$cmd" &
    fi

    # Сохраняем PID процесса
    PIDS+=($!)
done

# Ждём завершения всех процессов
wait
