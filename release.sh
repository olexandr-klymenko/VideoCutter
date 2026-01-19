#!/bin/bash

# Зчитуємо версію та видаляємо можливі зайві символи повернення каретки (CRLF)
VERSION=$(cat version.txt | tr -d '\r' | tr -d '[:space:]')
TAG="v$VERSION"

echo "--- Preparing release $TAG ---"

# Синхронізація тегів
git fetch --tags

# Перевірка на дублікат
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: Tag $TAG already exists!"
    exit 1
fi

# Процес Git
git add .
git commit -m "release: $TAG"
git tag -a "$TAG" -m "Release $TAG"

echo "Pushing to GitHub..."
git push origin master
git push origin "$TAG"

echo "--- Success! Version $TAG is on the way. ---"