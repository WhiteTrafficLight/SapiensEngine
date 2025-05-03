#!/bin/bash

echo "===== 서버 재시작 스크립트 ====="
echo "1. Python API 서버 중지 (실행 중인 경우)"
pkill -f "uvicorn api_server:app" || echo "No running Python API server found"

echo "2. Next.js 서버 중지 (실행 중인 경우)"
cd /Users/jihoon/sapiens_engine/agoramind
pkill -f "npm run dev" || echo "No running Next.js server found"

echo "3. Python API 서버 시작"
cd /Users/jihoon/sapiens_engine
nohup uvicorn api_server:app --reload --host 0.0.0.0 --port 8000 > python_api.log 2>&1 &
echo "Python API 서버가 백그라운드에서 시작되었습니다. 로그: python_api.log"

echo "4. Next.js 서버 시작"
cd /Users/jihoon/sapiens_engine/agoramind
nohup npm run dev > nextjs.log 2>&1 &
echo "Next.js 서버가 백그라운드에서 시작되었습니다. 로그: nextjs.log"

echo "5. 서버 상태 확인"
echo "잠시 후 서버가 완전히 시작됩니다. 로그를 확인하세요:"
echo "Python API 로그: tail -f /Users/jihoon/sapiens_engine/python_api.log"
echo "Next.js 로그: tail -f /Users/jihoon/sapiens_engine/agoramind/nextjs.log"
echo "===== 완료 =====" 