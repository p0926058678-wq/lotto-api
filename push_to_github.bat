
@echo off
REM 設定 Git 使用者資訊
git config --global user.name "lucky李"
git config --global user.email "p0926058678@gmail.com"

REM 初始化 Git 倉庫（如果尚未初始化）
if not exist .git (
    git init
)

REM 加入所有檔案並提交
git add .
git commit -m "Initial commit"

REM 建立 main 分支
git branch -M main

REM 設定 GitHub 遠端
git remote remove origin
git remote add origin https://github.com/p0926058678-wq/lotto-api.git

REM 推送到 GitHub
git push -u origin main

pause
