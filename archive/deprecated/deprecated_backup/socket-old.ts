import { Server } from 'socket.io';
import type { Server as HTTPServer } from 'http';
import type { NextApiRequest, NextApiResponse } from 'next';
import type { Socket } from 'net';
import { ChatMessage, ChatRoom } from '@/lib/ai/chatService';
import chatService from '@/lib/ai/chatService';
import chatRoomDB from '@/lib/db/chatRoomDB';
import fs from 'fs';
import path from 'path';

// Disable bodyParser to allow WebSocket upgrade
export const config = {
  api: {
    // WebSocket 연결과 POST 요청 모두 처리하기 위해 bodyParser를 자동으로 사용하지 않음
    bodyParser: false,
  },
};

// .env.local 파일에서 직접 API 키를 로드하는 함수
function loadEnvLocal() {
  try {
    // 프로젝트 루트 디렉토리 경로
    const rootDir = process.cwd();
    const envPath = path.join(rootDir, '.env.local');
    
    // .env.local 파일이 존재하는지 확인
    if (fs.existsSync(envPath)) {
      console.log('📁 socket.ts: .env.local 파일을 찾았습니다.');
      // 파일 내용 읽기
      const fileContent = fs.readFileSync(envPath, 'utf-8');
      // 각 줄을 파싱하여 환경 변수로 설정
      const vars = fileContent.split('\n')
        .filter(line => line && !line.startsWith('#'))
        .map(line => line.split('='))
        .reduce((acc, [key, value]) => {
          if (key && value) {
            acc[key.trim()] = value.trim();
          }
          return acc;
        }, {} as Record<string, string>);
      
      console.log('✅ socket.ts: .env.local 파일에서 설정을 로드했습니다.');
      return vars;
    } else {
      console.error('❌ socket.ts: .env.local 파일을 찾을 수 없습니다.');
      return {};
    }
  } catch (error) {
    console.error('❌ socket.ts: .env.local 파일 로드 중 오류 발생:', error);
    return {};
  }
}

// .env.local에서 설정 로드
const envVars = loadEnvLocal();

// API Key 설정 - .env.local에서 가져온 값을 우선 사용
const apiKey = envVars.OPENAI_API_KEY || process.env.OPENAI_API_KEY || '';
console.log('socket.ts - API Key source:', apiKey === envVars.OPENAI_API_KEY ? '.env.local 파일' : 'system 환경 변수');
console.log('socket.ts - API Key check:', apiKey ? `${apiKey.substring(0, 7)}...${apiKey.substring(apiKey.length - 4)}` : 'MISSING');

// 타입 정의 개선
interface SocketServer extends HTTPServer {
  io?: Server;
}

// Next.js에서 제공하는 타입 정의를 사용
interface NextApiResponseWithSocket extends NextApiResponse {
  socket: Socket & {
    server: HTTPServer & {
      io?: Server;
    };
  };
}

// 소켓 연결 관리를 위한 변수들
interface ConnectedUser {
  socketId: string;
  username: string;
  rooms: string[];
}

// 인터페이스 정의
interface JoinRoomData {
  roomId: string | number;
  username: string;
}

interface SendMessageData {
  roomId: string | number;
  message: string;
  sender: string;
}

interface GetActiveUsersData {
  roomId: string | number;
}

// 연결된 사용자와 소켓 매핑을 위한 객체
const connectedUsers: Record<string, ConnectedUser> = {};
const socketUserMapping: Record<string, string> = {};

let io: Server;

// 소켓 핸들러
const socketHandler = async (req: NextApiRequest, res: NextApiResponseWithSocket) => {
  // Enable CORS - 모든 오리진 허용
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'X-Requested-With, X-HTTP-Method-Override, Content-Type, Accept, Authorization');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  
  // OPTIONS(preflight) 요청 처리
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  // POST 요청 처리 - Python 서버로부터의 브로드캐스트 요청
  if (req.method === 'POST') {
    try {
      // POST 요청의 body를 수동으로 파싱
      const buffers: Buffer[] = [];
      
      for await (const chunk of req) {
        buffers.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
      }
      
      const data = Buffer.concat(buffers).toString();
      let body;
      
      try {
        body = data ? JSON.parse(data) : {};
        console.log('Socket API POST 요청 받음:', body);
      } catch (e) {
        console.error('JSON 파싱 에러:', e, 'Raw data:', data);
        return res.status(400).json({ error: 'Invalid JSON in request body' });
      }
      
      // Socket.IO 서버가 초기화되지 않았으면 오류 반환
      if (!res.socket?.server.io) {
        console.error('❌ Socket.IO 서버가 초기화되지 않았습니다.');
        return res.status(500).json({ error: 'Socket.IO server not initialized' });
      }
      
      const { action, room, event, data: eventData } = body;
      
      // 브로드캐스트 액션 처리
      if (action === 'broadcast') {
        if (!room || !event || !eventData) {
          return res.status(400).json({ error: 'Missing required fields: room, event, or data' });
        }
        
        console.log(`📢 브로드캐스트 요청 - 방: ${room}, 이벤트: ${event}`);
        
        // 특정 방에 이벤트 브로드캐스트
        res.socket.server.io.to(String(room)).emit(event, eventData);
        console.log(`✅ 브로드캐스트 완료 - ${room} 방의 모든 클라이언트에게 ${event} 이벤트 전송됨`);
        
        return res.status(200).json({ success: true, message: 'Broadcast sent' });
      }
      
      return res.status(400).json({ error: 'Invalid action' });
    } catch (error) {
      console.error('Socket API 에러:', error);
      return res.status(500).json({ error: 'Internal Server Error', details: error instanceof Error ? error.message : 'Unknown error' });
    }
  }

  if (req.method === 'GET') {
    if (!res.socket?.server.io) {
      try {
        console.log('Initializing socket server...');
        
        // @ts-ignore: Property 'server' does not exist on type 'Socket'.
        const httpServer = res.socket.server;
        
        io = new Server(httpServer, {
          path: '/api/socket/io',
          addTrailingSlash: false,
          cors: {
            origin: '*',
            methods: ['GET', 'POST', 'OPTIONS'],
            credentials: true,
            allowedHeaders: ['content-type', 'x-requested-with', 'authorization', 'accept']
          },
          allowEIO3: true, // Socket.IO v3 클라이언트 지원
          connectTimeout: 45000, // 연결 시간 증가
          pingTimeout: 30000,   // 핑 타임아웃 증가
          transports: ['websocket', 'polling'] // 웹소켓 우선, 폴링 백업
        });
        
        // @ts-ignore: Property 'io' does not exist on type 'Server'.
  res.socket.server.io = io;

  io.on('connection', (socket) => {
          console.log(`New client connected: ${socket.id}`);
          
          socket.on('join-room', (data: { roomId: string | number, username: string }) => {
            const roomId = String(data.roomId);
            socket.join(roomId);
            console.log(`User ${data.username} joined room ${roomId}`);
            
            // 사용자 연결 정보 관리
            const socketId = socket.id;
            if (!connectedUsers[socketId]) {
              connectedUsers[socketId] = {
                socketId,
                username: data.username,
                rooms: [roomId]
              };
            } else {
              // 이미 있으면 방 목록에 추가
              if (!connectedUsers[socketId].rooms.includes(roomId)) {
                connectedUsers[socketId].rooms.push(roomId);
              }
            }
            
            // 사용자명으로 소켓 ID를 찾을 수 있도록 매핑
            socketUserMapping[data.username] = socketId;
            
            // 방에 있는 사용자 목록 가져오기
            const usersInRoom = getUsersInRoom(roomId);
            
            // Notify all clients in the room that a user has joined
            io.to(roomId).emit('user-joined', { 
              roomId,
              username: data.username,
              usersInRoom
            });
          });
          
          socket.on('leave-room', async (data: { roomId: string | number, username: string }) => {
            const roomId = String(data.roomId);
            socket.leave(roomId);
            console.log(`User ${data.username} left room ${roomId}`);
            
            // 사용자 연결 정보에서 방 제거
            const socketId = socket.id;
            if (connectedUsers[socketId]) {
              connectedUsers[socketId].rooms = connectedUsers[socketId].rooms
                .filter(r => r !== roomId);
            }
            
            // 방에 있는 사용자 목록 가져오기
            const usersInRoom = getUsersInRoom(roomId);
            
            // Notify all clients in the room that a user has left
            io.to(roomId).emit('user-left', { 
              roomId,
              username: data.username,
              usersInRoom
            });
            
            // 사용자가 모두 나갔는지 확인
            const clientsInRoom = io.sockets.adapter.rooms.get(roomId);
            const isRoomEmpty = !clientsInRoom || clientsInRoom.size === 0;
            
            if (isRoomEmpty) {
              console.log(`🚨 방 ${roomId}에 남은 사용자가 없습니다. 자동 대화 모드 종료 시도...`);
              
              try {
                // 자동 대화 상태 확인
                const autoConvStatusResponse = await fetch(`http://localhost:8000/api/auto-conversation/status?room_id=${roomId}`, {
                  method: 'GET',
                  headers: {
                    'Accept': 'application/json'
                  }
                });
                
                if (autoConvStatusResponse.ok) {
                  const statusData = await autoConvStatusResponse.json();
                  const isAutoConversationActive = statusData.active === true;
                  
                  if (isAutoConversationActive) {
                    console.log(`🔍 방 ${roomId}의 자동 대화 모드가 활성화 상태입니다. 종료합니다.`);
                    
                    // 자동 대화 모드 종료 요청
                    const stopResponse = await fetch(`http://localhost:8000/api/auto-conversation`, {
                      method: 'DELETE',
                      headers: {
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                        room_id: roomId
                      })
                    });
                    
                    if (stopResponse.ok) {
                      console.log(`✅ 방 ${roomId}의 자동 대화 모드가 성공적으로 종료되었습니다.`);
                    } else {
                      console.error(`❌ 방 ${roomId}의 자동 대화 모드 종료 실패: ${stopResponse.status} ${stopResponse.statusText}`);
                    }
                  } else {
                    console.log(`ℹ️ 방 ${roomId}의 자동 대화 모드가 이미 비활성화 상태입니다.`);
                  }
                } else {
                  console.warn(`⚠️ 방 ${roomId}의 자동 대화 상태 확인 실패: ${autoConvStatusResponse.status} ${autoConvStatusResponse.statusText}`);
                }
              } catch (error) {
                console.error(`❌ 자동 대화 모드 종료 중 오류:`, error);
              }
            }
          });
          
          socket.on('send-message', async (data: any) => {
            // Log the raw data first
            console.log(`🚨 socket.id ${socket.id} send-message RAW data:`, data);
            
            if (!data || typeof data !== 'object') {
              console.error('❌ Invalid send-message data format:', data);
              return;
            }
            
            // Ensure we have the required fields
            if (!data.roomId || !data.message) {
              console.error('❌ Missing roomId or message in send-message event:', data);
              return;
            }
            
            // Convert roomId to string and ensure message has all required fields
            const roomId = String(data.roomId);
            const message = data.message;
            
            // Note: RAG parameter is now ignored as the server auto-detects it
            // This is kept for backward compatibility but will be removed in future
            const useRAG = data.useRAG || false;
            if (useRAG) {
              console.log(`ℹ️ Client requested RAG, but server will auto-detect instead`);
            }
            
            console.log(`🚨 'send-message' 이벤트 수신 - 방 ID: ${roomId}, 메시지:`, message);
            
            // Ensure timestamp is a Date object
            if (message.timestamp && typeof message.timestamp === 'string') {
              message.timestamp = new Date(message.timestamp);
            }
            
            // MongoDB에 메시지 저장
            try {
              console.log(`💾 MongoDB에 메시지 저장 중: ${message.text.substring(0, 30)}...`);
              const success = await chatRoomDB.addMessage(roomId, message);
              
              if (success) {
                console.log('✅ 메시지가 MongoDB에 저장되었습니다.');
              } else {
                console.warn('⚠️ 메시지 저장에 실패했습니다 (중복 또는 ID 오류)');
              }
            } catch (error) {
              console.error('❌ MongoDB 저장 오류:', error);
            }
            
            // Broadcast the message to all clients in the room
            console.log(`📢 메시지 브로드캐스트 [방 ${roomId}]: ${JSON.stringify({ id: message.id, text: message.text.substring(0, 20) + '...', sender: message.sender })}`);
            console.log(`📊 현재 방(${roomId})에 연결된 클라이언트 수: ${io.sockets.adapter.rooms.get(roomId)?.size || 0}명`);
            
            // 발신자 자신에게는 메시지를 다시 보내지 않음
            // socket.broadcast.to(roomId)로 변경하여 자신을 제외한 방의 다른 사용자들에게만 브로드캐스트
            socket.broadcast.to(roomId).emit('new-message', {
              roomId: roomId,
              message: message
            });
            console.log(`✅ 브로드캐스트 완료 - 발신자 제외 방송`);
            
            // AI 응답 생성
            try {
              // 메시지가 사용자로부터 온 경우에만 AI 응답 생성
              if (message.isUser) {
                console.log(`🤖 AI 응답 생성 중... 방 ID: ${roomId}`);
                
                // 방정보 가져오기
                const room = await chatRoomDB.getChatRoomById(roomId);
                if (!room) {
                  console.error(`❌ 채팅방을 찾을 수 없음: ${roomId}`);
                  return;
                }
                
                // 자동 대화 모드 확인
                let isAutoConversationActive = false;
                try {
                  // Python API에 자동 대화 상태 확인 요청
                  const autoConvStatusResponse = await fetch(`http://localhost:8000/api/auto-conversation/status?room_id=${roomId}`, {
                    method: 'GET',
                    headers: {
                      'Accept': 'application/json'
                    }
                  });
                  
                  if (autoConvStatusResponse.ok) {
                    const statusData = await autoConvStatusResponse.json();
                    isAutoConversationActive = statusData.active === true;
                    console.log(`🔍 자동 대화 모드 확인 결과: ${isAutoConversationActive ? '활성화됨' : '비활성화됨'}`);
                  } else {
                    console.warn(`⚠️ 자동 대화 상태 확인 실패, 기본값(비활성화)으로 진행`);
                  }
                } catch (error) {
                  console.error(`❌ 자동 대화 상태 확인 중 오류:`, error);
                  // 오류 발생 시 기본값으로 자동 대화 비활성화 상태로 간주
                }
                
                // 자동 대화 모드가 비활성화된 경우에만 API 호출
                if (!isAutoConversationActive) {
                  // 직접 API 호출로 AI 응답 생성
                  console.log(`🔍 자동 대화 모드 비활성화 - AI API 요청 시작 - 방 ID: ${roomId}, 메시지 수: ${room?.messages?.length || 0}`);
                
                  // API 요청 페이로드 로깅 (민감한 내용은 제한적으로)
                  const requestPayload = {
                    room_id: roomId,
                    user_message: message.text,
                    npcs: room?.participants?.npcs || [],
                    topic: room?.title,
                    context: room?.context?.substring(0, 50) + '...',
                  };
                  console.log('📤 API 요청 페이로드:', JSON.stringify(requestPayload));
                  
                  // Python 백엔드 직접 호출 (Next.js API 우회)
                  const pythonBackendUrl = 'http://localhost:8000/api/chat/generate';
                  console.log('🔗 Python API URL:', pythonBackendUrl);
                  
                  // API 키 가져오기
                  if (!apiKey) {
                    console.error('❌ OpenAI API 키가 설정되지 않았습니다.');
                    throw new Error('OpenAI API key is not set');
                  }
                  
                  const response = await fetch(pythonBackendUrl, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                      room_id: roomId,
                      user_message: message.text,
                      npcs: room?.participants?.npcs || [],
                      topic: room?.title,
                      context: room?.context,
                      llm_provider: 'openai',
                      llm_model: 'gpt-4o',
                      api_key: apiKey
                    }),
                  });
                  
                  console.log(`🔍 Python API 응답 상태: ${response.status} ${response.statusText}`);
                  
                  if (!response.ok) {
                    const errorText = await response.text().catch(() => 'Cannot read error response');
                    console.error(`❌ Python API 응답 오류: 상태 ${response.status}, 텍스트: ${errorText}`);
                    throw new Error(`Python API 응답 오류: ${response.status}`);
                  }

                  // Python API 응답 처리 및 메시지 구성
                  const responseData = await response.json();
                  console.log('📥 Python API 응답 데이터:', JSON.stringify(responseData).substring(0, 200) + '...');
                  
                  // 인용 정보 로깅
                  if (responseData.citations && Array.isArray(responseData.citations)) {
                    console.log(`📚 인용 정보 ${responseData.citations.length}개 발견:`, JSON.stringify(responseData.citations));
                  }
                  
                  // 응답 데이터 추출 (Python 백엔드 형식)
                  if (responseData && responseData.response && responseData.philosopher) {
                    // Python 백엔드로부터 받은 정보로 메시지 객체 생성
                    const aiMessage = {
                      id: `ai-${Date.now()}`,
                      text: responseData.response,
                      sender: responseData.philosopher,
                      senderType: "npc",
                      isUser: false,
                      timestamp: new Date(),  // Date 객체로 생성
                      metadata: responseData.metadata || {},
                      citations: responseData.citations || [] // Add citations from Python backend
                    };
                    
                    // 인용 정보가 있는 경우 추가 로깅
                    if (responseData.citations && Array.isArray(responseData.citations) && responseData.citations.length > 0) {
                      console.log(`📚 AI 메시지에 ${responseData.citations.length}개의 인용 정보가 포함됨`);
                    }
                    
                    // MongoDB에 AI 메시지 저장
                    try {
                      await chatRoomDB.addMessage(roomId, aiMessage);
                      console.log(`✅ AI 메시지(${aiMessage.id})가 MongoDB에 저장되었습니다.`);
                    } catch (dbError) {
                      console.error('❌ AI 메시지 MongoDB 저장 오류:', dbError);
                    }
                    
                    // 클라이언트에 AI 메시지 전송
                    io.to(roomId).emit('new-message', {
                      roomId: roomId,
                      message: aiMessage
                    });
                    console.log(`✅ AI 응답 브로드캐스트 완료 - 모든 클라이언트에게 전송됨`);
                  } else {
                    console.error('❌ 유효하지 않은 AI 응답 형식:', responseData);
                    throw new Error('Invalid AI response format');
                  }
                } else {
                  // 자동 대화 모드가 활성화된 경우
                  console.log(`🔍 자동 대화 모드 활성화됨 - /api/chat 호출 생략`);
                  console.log(`🔍 사용자 메시지는 자동 대화 컨텍스트에 자연스럽게 통합될 예정`);
                }
              }
            } catch (error) {
              console.error('❌ AI 응답 생성 오류:', error);
              
              // 오류 시 기본 응답자 설정 시도
              try {
                const room = await chatRoomDB.getChatRoomById(roomId);
                const defaultSender = room?.participants?.npcs?.[0] || "System";
                
                // 기본 에러 메시지 전송
                const errorMessage = {
                  id: `error-${Date.now()}`,
                  text: "I'm processing your request. Please give me a moment to respond.",
                  sender: defaultSender,
                  isUser: false,
                  timestamp: new Date()
                };
                
                // 에러 메시지 브로드캐스트
                io.to(roomId).emit('new-message', {
                  roomId: roomId,
                  message: errorMessage
                });
                console.log(`✅ 오류 메시지 브로드캐스트 완료 - 모든 클라이언트에게 전송됨`);
              } catch (msgError) {
                console.error('Failed to send error message:', msgError);
              }
            }
          });

          socket.on('room-created', (room: ChatRoom) => {
            console.log(`New chat room created: ${room.title}`);
            
            // Broadcast to all clients that a new room was created
            io.emit('room-created', room);
          });
          
          socket.on('disconnect', () => {
            console.log(`Client disconnected: ${socket.id}`);
            
            // 연결 해제된 사용자 정보 정리
            const disconnectedUser = connectedUsers[socket.id];
            if (disconnectedUser) {
              // 해당 사용자가 참여하고 있던 모든 방에 떠났음을 알림
              disconnectedUser.rooms.forEach(roomId => {
                const usersInRoom = getUsersInRoom(roomId).filter(u => u !== disconnectedUser.username);
                io.to(roomId).emit('user-left', {
                  roomId,
                  username: disconnectedUser.username,
                  usersInRoom
                });
              });
              
              // 사용자 정보 삭제
              delete socketUserMapping[disconnectedUser.username];
              delete connectedUsers[socket.id];
            }
          });
          
          // 특정 방에 있는 활성 사용자 목록 조회
          socket.on('get-active-users', (roomId: string | number) => {
            const roomIdStr = String(roomId);
            console.log(`Getting active users for room: ${roomIdStr}`);
            
            const usersInRoom = getUsersInRoom(roomIdStr);
            socket.emit('active-users', {
              roomId: roomIdStr,
              users: usersInRoom
            });
          });
          
          // Simple ping handler for connection testing
          socket.on('ping', (data: { time: number, username: string }) => {
            console.log(`📡 PING received from ${data.username}, time: ${new Date(data.time).toISOString()}`);
            
            // Send back a pong with round-trip time
            socket.emit('pong', {
              time: data.time,
              serverTime: Date.now()
            });
            
            console.log(`📡 PONG sent back to ${data.username}`);
          });
          
          // Handle broadcast requests from Python backend
          socket.on('broadcast-to-room', (data: { room_id: string, event: string, data: any }) => {
            console.log(`📢 Python 백엔드로부터 브로드캐스트 요청: 방 ${data.room_id}, 이벤트 ${data.event}`);
            
            // Broadcast to all clients in the specified room
            io.to(data.room_id).emit(data.event, data.data);
            
            console.log(`✅ 브로드캐스트 완료: 방 ${data.room_id}에 ${data.event} 이벤트 전송됨`);
          });
        });

        console.log('Socket.IO server initialized');
        
      } catch (error) {
        console.error('Socket server initialization error:', error);
        return res.status(500).json({ error: 'Failed to initialize socket server', details: error instanceof Error ? error.message : 'Unknown error' });
      }
    } else {
      console.log('Socket server already running');
    }
    
    return res.status(200).json({ success: true, message: 'Socket server running' });
  } else {
    return res.status(405).json({ error: 'Method not allowed' });
  }
};

// 특정 방에 있는 활성 사용자 목록 구하기
function getUsersInRoom(roomId: string): string[] {
  const usersInRoom: string[] = [];
  
  Object.values(connectedUsers).forEach(user => {
    if (user.rooms.includes(roomId)) {
      usersInRoom.push(user.username);
    }
  });
  
  return usersInRoom;
}

// Export the handler
export default socketHandler; 