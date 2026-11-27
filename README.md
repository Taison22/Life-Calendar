# Life Calendar — Календарь жизни (v1.2)

Desktop-приложение для визуализации жизни в неделях.

**Версия 1.2** — technical hardening: надёжность SQLite, безопасный импорт, кэш, тесты, документация.

## Возможности

- Интерактивная сетка до 90×52 (недели жизни от дня рождения)
- Цвета: прошлое / текущая / будущее / события пользователя
- События с категориями, заметками и цветом; создание и редактирование
- Статистика (возраст, недели, дни, процент, прогресс)
- Список событий с поиском и фильтром
- Локальное хранение SQLite (WAL + foreign_keys)
- Экспорт / импорт JSON с автоматическим backup и откатом при ошибке
- Тёмная минималистичная тема

## Требования

- Python 3.10+
- customtkinter
- tkinter (входит в стандартную установку Python)

## Установка и запуск

### Windows 10/11

1. Установите Python: https://www.python.org/downloads/
   Отметьте **Add python.exe to PATH**.
2. В папке проекта:
   ```powershell
   pip install -r requirements.txt
   python run.py
   ```

### Linux / macOS

```bash
pip install -r requirements.txt
python3 run.py
```

## Первый запуск

Укажите дату рождения (ГГГГ-ММ-ДД) и ожидаемую продолжительность жизни.
База `data/life_calendar.db` создаётся автоматически.

## Расположение данных

| Что | Где |
|-----|-----|
| Основная БД | `data/life_calendar.db` |
| Авто-backup перед импортом | `data/life_calendar_backup_YYYYMMDD_HHMMSS.db` |

Папка `data/` с пользовательскими `.db` не должна попадать в Git (см. `.gitignore`).

## Обновление с 1.1

1. Сделайте копию своей `data/life_calendar.db`.
2. Замените код на версию 1.2.
3. Запустите приложение — миграция схемы выполнится автоматически. Данные сохраняются.

## Структура проекта

```
life-calendar-py/
├── run.py
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── .gitignore
├── data/
├── src/
│   ├── main.py
│   ├── database.py
│   └── calculations.py
└── tests/
    ├── test_calculations.py
    ├── test_database.py
    └── test_cache_logic.py
```

## Тесты

```bash
python tests/test_calculations.py
python tests/test_database.py
python tests/test_cache_logic.py
```

Тесты БД используют временный каталог и не трогают реальную базу.

## Концепция сетки

Каждая строка — год жизни от дня рождения.
Каждый столбец — неделя этого года (0…51).
Настройка «первый день недели» влияет только на вспомогательные функции и не меняет сетку жизни.

## Сборка .exe (опционально)

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name LifeCalendar run.py
```
