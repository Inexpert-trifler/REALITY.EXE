#!/bin/bash
git init
echo "node_modules/" > .gitignore
echo "dist/" >> .gitignore
echo ".env" >> .gitignore

git add .gitignore
git commit -m "chore: initial commit with gitignore"

FILES=$(find src -type f | sort)
COUNT=1

for FILE in $FILES; do
  git add "$FILE"
  git commit -m "feat: add $(basename $FILE)"
  COUNT=$((COUNT+1))
done

# Commit everything else remaining in the root folder
git add package.json package-lock.json tsconfig.json vite.config.ts postcss.config.cjs tailwind.config.cjs index.html DESIGN.md docs/ overworld_tactile_pixel/ reality.exe_game_master_verification/ reality.exe_home_base/ reality.exe_player_profile/ reality.exe_pocket_mode/ reality.exe_quest_complete/ reality.exe_quest_ready/ reality.exe_quest_setup/ reality.exe_welcome_back/
git commit -m "chore: add configuration and documentation files"

git remote add origin https://github.com/Inexpert-trifler/REALITY.EXE.git
git branch -M main

# Display commit count
git log --oneline | wc -l
