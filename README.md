# KarmaSystem — лендинг

Минимальный одностраничный сайт + простой Node/Express сервер для статики.

## Запуск локально

```bash
npm install
npm run dev    # или: npm start
# открой http://localhost:3000
```

## Структура
```
WebKarmaApp/
├── public/
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── package.json
├── server.js
└── README.md
```

## Публикация в ваш репозиторий GitHub

Вариант A — через командную строку:

```bash
cd /путь/к/WebKarmaApp
git init
git add .
git commit -m "Initial commit: KarmaSystem landing"
git branch -M main
git remote add origin https://github.com/Djju69/WebKarmaApp.git
git push -u origin main
```

Если `origin` уже существует:
```bash
git remote remove origin
git remote add origin https://github.com/Djju69/WebKarmaApp.git
git push -u origin main
```

Вариант B — GitHub Desktop:
1. File → Add local repository → выберите папку `WebKarmaApp`
2. Commit to main
3. Push origin

## Деплой на Railway

1. Создайте новый проект → Deploy from GitHub repo → выберите `WebKarmaApp`
2. Railway автоматически определит Node.js приложение и запустит деплой
3. После деплоя получите URL

**Важно:** переменных окружения не требуется. Порт берётся из `process.env.PORT`.
