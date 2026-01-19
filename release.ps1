# 1. Перевірка файлу версії
if (-Not (Test-Path "version.txt")) {
    Write-Host "Помилка: Файл version.txt не знайдено!" -ForegroundColor Red
    exit
}

$version = (Get-Content version.txt).Trim()
$tag = "v$version"

Write-Host "--- Підготовка релізу $tag ---" -ForegroundColor Cyan

# 2. Оновлюємо теги з сервера
git fetch --tags

# 3. Перевіряємо чи таг вже існує
$tagExists = git tag -l $tag
if ($tagExists) {
    Write-Host "Помилка: Таг $tag вже існує. Оновіть версію у version.txt" -ForegroundColor Red
    exit
}

# 4. Процес Git
try {
    Write-Host "Створення коміту та тегу..." -ForegroundColor Yellow
    git add .
    git commit -m "release: $tag"
    git tag -a $tag -m "Release $tag"

    Write-Host "Відправка в GitHub (master та $tag)..." -ForegroundColor Yellow
    git push origin master
    git push origin $tag

    Write-Host "--- Успіх! Версія $tag відправлена. ---" -ForegroundColor Green
}
catch {
    Write-Host "Сталася помилка під час роботи з Git." -ForegroundColor Red
}