name: FOFA IP TV Scanner

on:
  schedule:
    # 安全调度：每天运行2次
    - cron: "0 6 * * *"   # 每天UTC时间6点（北京时间14点）
    - cron: "0 18 * * *"  # 每天UTC时间18点（北京时间次日2点）
  workflow_dispatch:       # 手动触发

jobs:
  fetch-and-push:
    runs-on: ubuntu-latest
    timeout-minutes: 30    # 设置超时，防止长时间运行

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
        with:
          persist-credentials: true
          fetch-depth: 1   # 只获取最近提交，加快速度

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Install ffmpeg
        run: |
          sudo apt-get update
          sudo apt-get install -y ffmpeg
          echo "🟢 ffmpeg 安装完成"

      - name: Run fofa_fetch.py
        run: |
          echo "🕒 当前时间: $(date)"
          echo "🔍 开始执行 FOFA 爬取脚本..."
          python fofa_fetch.py
        env:
          PYTHONUNBUFFERED: 1

      - name: Check if there are changes
        id: check-changes
        run: |
          git add 计数.txt ip/*.txt IPTV.txt || true
          if git diff --staged --quiet; then
            echo "🟡 没有检测到文件变化"
            echo "has_changes=false" >> $GITHUB_OUTPUT
          else
            echo "🟢 检测到文件变化，准备提交"
            echo "has_changes=true" >> $GITHUB_OUTPUT
          fi

      - name: Commit and push changes
        if: steps.check-changes.outputs.has_changes == 'true'
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git commit -m "自动更新：FOFA IP数据 $(date +'%Y-%m-%d %H:%M')"
          git push origin main
        env:
          GIT_HTTP_TIMEOUT: 30

      - name: No changes found
        if: steps.check-changes.outputs.has_changes == 'false'
        run: echo "🟡 本次运行没有产生新变化，跳过提交"
