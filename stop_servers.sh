#!/bin/bash

echo "===== 서버 종료 스크립트 ====="
echo "1. Python API 서버 종료 시도"
pkill -f "uvicorn api_server:app" && echo "Python API 서버가 종료되었습니다." || echo "실행 중인 Python API 서버가 없습니다."

echo "2. Next.js 서버 종료 시도"
pkill -f "npm run dev" && echo "Next.js 서버가 종료되었습니다." || echo "실행 중인 Next.js 서버가 없습니다."

echo "3. 서버 프로세스 상태 확인"
ps_output=$(ps aux | grep -E "uvicorn|npm run dev" | grep -v grep)

if [ -z "$ps_output" ]; then
  echo "✅ 모든 서버가 정상적으로 종료되었습니다."
else
  echo "⚠️ 아직 실행 중인 서버 프로세스가 있습니다:"
  echo "$ps_output"
  echo "강제 종료가 필요하면 다음 명령어를 실행하세요:"
  echo "pkill -9 -f \"uvicorn api_server:app\" && pkill -9 -f \"npm run dev\""
fi

echo "===== 완료 =====" 