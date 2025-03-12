# Telegram Support Bot

## Описание

Этот бот предназначен для организации службы поддержки в Telegram. Он позволяет пользователям создавать заявки, а операторам — обрабатывать их, вести диалог и закрывать тикеты.

## Функции

- ✅ **Создание заявок** пользователями
- ✅ **Категории заявок** (ошибка, улучшение, вопрос)
- ✅ **Чат между оператором и пользователем** внутри бота
- ✅ **Назначение операторов** и управление ролями
- ✅ **Отправка изображений** в тикетах
- ✅ **Проверка подписки на канал** перед началом работы
- ✅ **Асинхронная работа с PostgreSQL**
- ✅ **Антифлуд-механизм** через middleware

## Установка и запуск

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Создание .env файла

Создайте файл `.env` и добавьте туда свои данные:

```env
BOT_TOKEN=your_bot_token
DB_URL=postgresql://user:password@localhost:5432/dbname
CHANNEL_ID=@yourchannel  # Канал для проверки подписки
```

### 3. Запуск бота

```bash
python bot.py
```

## Технические детали

### Структура проекта

```
📁 TelegramSupportBot
├── bot.py        # Основной код бота
├── admin.py      # Логика для операторов
├── chat.py       # Логика общения операторов и пользователей
├── database.py   # Работа с PostgreSQL
├── anty_ddos.py  # Middleware для защиты от спама
├── .env          # Файл с переменными окружения
├── requirements.txt # Список зависимостей
```

### База данных

Используется **PostgreSQL** с таблицами:

- `users (user_id, state, role, category)`
- `tickets (ticket_id, user_id, text, status, created_at, operator_id)`

## Контакты

Если у вас есть вопросы или предложения, пишите в [Telegram](https://t.me/alexsmilex).

