Первый запуск:

1. Создать виртуальное окружение:
    python -m venv .venv

2. Активировать виртуальное окружение:
   .\.venv\Scripts\activate

3. Установить зависимости (путь: "...\site"):
  pip install -r requirements.txt

4. Запустить:
   uvicorn app.main:app --reload

Запуск:

1. Зайти в папку проекта:
    cd site
    
2. Активировать окружение:
    .venv\Scripts\activate.bat

3. Запустить сайт:
   python -m uvicorn app.main:app --reload
