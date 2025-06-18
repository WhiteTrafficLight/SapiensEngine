import { io, Socket } from 'socket.io-client';
import { ChatMessage, Citation } from '@/lib/ai/chatService';

// Type definitions for events
interface ServerToClientEvents {
  'new-message': (data: { roomId: string, message: ChatMessage }) => void;
  'thinking': (data: { sender: string }) => void;
  'auto-thinking': (data: { npc_id: string }) => void;
  'auto-message-sent': (data: {}) => void;
  'npc-selected': (data: { npc_id: string, npc_name?: string }) => void;
  'user-joined': (data: { username: string; usersInRoom: string[]; participants: any }) => void;
  'user-left': (data: { username: string; usersInRoom: string[] }) => void;
  'active-users': (data: { roomId: string; users: string[] }) => void;
  'error': (data: { message: string }) => void;
  'room-created': (data: { roomId: string; roomName: string }) => void;
  'pong': (data: { time: number, serverTime: number }) => void;
}

interface ClientToServerEvents {
  'join-room': (data: { roomId: string | number; username: string }) => void;
  'leave-room': (data: { roomId: string | number; username: string }) => void;
  'send-message': (data: { roomId: string | number; message: ChatMessage; useRAG?: boolean }) => void;
  'get-active-users': (roomId: string | number) => void;
  'ping': (data: { time: number, username: string }) => void;
  'refresh-room': (data: { roomId: string | number }) => void;
  'join': (data: { roomId: string | number }) => void;
  'leave': (data: { roomId: string | number }) => void;
  [event: string]: (...args: any[]) => void;  // Allow any other event
}

// Custom event handler type
interface EventHandler<T> {
  (data: T): T;
}

// Socket.io client wrapper class
class SocketClient {
  private socket: Socket<ServerToClientEvents, ClientToServerEvents> | null = null;
  private isInitialized: boolean = false;
  private username: string = '';
  private rooms: number[] = []; // 참여 중인 채팅방 ID 목록
  private listeners: Record<string, Function[]> = {
    'new-message': [],
    'thinking': [],
    'auto-thinking': [],
    'auto-message-sent': [],
    'npc-selected': [],
    'user-joined': [],
    'user-left': [],
    'active-users': [],
    'error': [],
    'connect': [],
    'disconnect': []
  };
  
  // Add custom event handlers storage
  private eventHandlers: Record<string, EventHandler<any>> = {};
  
  // Initialize the socket connection
  public async init(username: string = 'User'): Promise<SocketClient> {
    this.username = username;
    
    // ❶ 서버에 SocketHandler를 한 번 띄워 줍니다 - await the fetch
    try {
      console.log('Initializing server socket handler...');
      
      // 서버 초기화 방식 수정 - GET 요청 사용
      const res = await fetch('/api/socket', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        }
      });
      
      if (!res.ok) {
        const errorText = await res.text().catch(() => 'Unknown error');
        console.error(`Socket initialization failed with status: ${res.status}, message: ${errorText}`);
        throw new Error(`Failed to initialize socket server: ${res.status}`);
      } else {
        console.log('✅ Server socket handler ready');
      }
    } catch (error) {
      console.error('Error fetching /api/socket:', error);
      // 오류를 기록하되 계속 진행
      console.log('Attempting to connect directly to socket server...');
    }
    
    // Clean up any existing connection
    if (this.socket) {
      this.socket.disconnect();
    }
    
    // 네트워크 주소 확인 및 설정
    // 내부 개발 환경에서 localhost나 IP 주소를 자동으로 감지하여 사용
    const getSocketUrl = () => {
      // 브라우저 환경에서만 실행
      if (typeof window === 'undefined') return '';
      
      // 현재 URL 정보 가져오기
      const currentUrl = window.location.origin;
      console.log('Current URL:', currentUrl);
      
      // 명시적인 환경변수 값이 있으면 그것을 사용
      if (process.env.NEXT_PUBLIC_SOCKET_URL) {
        return process.env.NEXT_PUBLIC_SOCKET_URL;
      }
      
      // 현재 접속 URL 사용 (LAN 환경에서 접속 시 IP 주소 자동 감지)
      return currentUrl;
    };
    
    // Socket.IO 연결 URL 생성
    const socketUrl = getSocketUrl();
    console.log('Connecting to socket server at:', socketUrl);
    
    // Connection 로그 메시지 출력 (디버깅 및 사용자 안내용)
    console.log(`
==== Socket.IO Connection Info ====
URL: ${socketUrl}
Path: /api/socket/io
User: ${username}
Time: ${new Date().toLocaleTimeString()}
================================
    `);
    
    // Create new socket connection with improved options
    this.socket = io(socketUrl, {
      path: '/api/socket/io', // ⚡️ Must match server's path setting exactly!
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 10,  // 재연결 시도 횟수 증가
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000, // 최대 10초까지 지수적으로 대기
      timeout: 30000,  // 타임아웃 증가
      transports: ['websocket', 'polling'], // 웹소켓 먼저 시도, 실패 시 폴링으로 폴백
      forceNew: true,
      auth: {
        username: username,
        clientId: `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
      },
      extraHeaders: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });
    
    // Socket.IO 연결 디버깅 함수 추가
    this._setupDebugListeners(socketUrl);
    
    // Bind event listeners
    this._bindEvents();
    
    // Wait for connection or timeout
    try {
      await this._waitForConnection(5000);
    } catch (err) {
      console.warn('Socket connection timeout or error, continuing anyway:', err);
    }
    
    // Return this instance explicitly with the SocketClient type
    return this as SocketClient;
  }
  
  // Helper method to wait for connection with timeout
  private _waitForConnection(timeoutMs: number): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      // If already connected, resolve immediately
      if (this.socket?.connected) {
        resolve();
        return;
      }
      
      // Wait for connect event
      const onConnectSuccess = () => {
        console.log('Socket connected in waitForConnection promise');
        this.socket?.off('connect_error', onConnectError);
        clearTimeout(timeoutId);
        resolve();
      };
      
      // Handle connection error
      const onConnectError = (err?: any) => {
        console.error('Socket connection error in waitForConnection promise:', err);
        this.socket?.off('connect', onConnectSuccess);
        clearTimeout(timeoutId);
        reject(new Error('Socket connection error'));
      };
      
      // Set a timeout to avoid hanging
      const timeoutId = setTimeout(() => {
        console.warn('Socket connection timed out in waitForConnection promise');
        this.socket?.off('connect', onConnectSuccess);
        this.socket?.off('connect_error', onConnectError);
        reject(new Error('Socket connection timeout'));
      }, timeoutMs);
      
      // Listen for connection events
      this.socket?.once('connect', onConnectSuccess);
      this.socket?.once('connect_error', onConnectError);
    });
  }
  
  // Socket.IO 연결 디버깅을 위한 리스너 설정
  private _setupDebugListeners(socketUrl: string) {
    if (!this.socket) return;
    
    // 연결 오류 리스너
    this.socket.on('connect_error', (err) => {
      console.error('Socket connection error:', err.message);
      // 연결 정보 출력 (타입 안전하게)
      console.log('Socket ID:', this.socket?.id || 'unknown');
      console.log('Connected:', this.socket?.connected || false);
      console.log('Current URL:', window.location.href);
      console.log('Socket URL being used:', socketUrl);
      console.log('Socket Transport:', this.socket?.io?.engine?.transport?.name || 'unknown');
      
      // Socket.IO 타임아웃 오류인 경우 추가 정보 표시
      if (err.message === 'timeout') {
        console.error('Connection timed out. Check if server is running and accessible from your network.');
        console.log('If you are connecting from a different device, make sure both devices are on the same network.');
        console.log('You might need to allow connections through your firewall or antivirus.');
      }
      
      // 웹소켓 관련 오류인 경우 추가 정보
      if (err.message.includes('websocket')) {
        console.error('WebSocket error detected. This might be due to:');
        console.log('1. Proxy or firewall blocking WebSocket connections');
        console.log('2. Network configuration issues between client and server');
        console.log('3. Browser WebSocket implementation issues');
        console.log('Attempting to use polling as a fallback...');
        
        // 소켓 설정 수정 시도 - 폴링으로만 시도
        if (this.socket?.io) {
          this.socket.io.opts.transports = ['polling'];
          console.log('Changed transport to polling only');
        }
      }
      
      // 서버 오류인 경우 추가 정보 표시 
      if (err.message === 'server error') {
        console.error('Server error occurred. The socket.io server might be misconfigured or experiencing issues.');
        console.log('Try restarting the server with "npm run dev"');
        
        // 1초 후 재연결 시도 
        setTimeout(() => {
          console.log('Attempting to reconnect...');
          this.socket?.connect();
        }, 1000);
      }
      
      // 디버깅: 글로벌 창에 소켓 에러 설정
      if (typeof window !== 'undefined') {
        // @ts-ignore
        if (!window._socketDebug) window._socketDebug = {};
        // @ts-ignore
        window._socketDebug.error = err.message;
        // @ts-ignore
        window._socketDebug.connected = false;
      }
    });
    
    // 연결 이벤트
    this.socket.on('connect', () => {
      console.log('Socket successfully connected!');
      console.log('Socket ID:', this.socket?.id);
      console.log('Transport:', this.socket?.io?.engine?.transport?.name || 'unknown');
      
      // 디버깅: 글로벌 창에 소켓 ID 설정
      if (typeof window !== 'undefined') {
        // @ts-ignore
        if (!window._socketDebug) window._socketDebug = {};
        // @ts-ignore
        window._socketDebug.socketId = this.socket?.id;
        // @ts-ignore
        window._socketDebug.connected = true;
        // @ts-ignore
        window._socketDebug.url = this.socket?.io.uri;
      }
    });
    
    // 연결 끊김 이벤트
    this.socket.on('disconnect', (reason) => {
      console.log(`Socket disconnected. Reason: ${reason}`);
      
      // 서버 측 연결 끊김인 경우에만 자동 재연결 시도
      if (reason === 'io server disconnect' || reason === 'transport error') {
        console.log('Attempting to reconnect in 2 seconds...');
        setTimeout(() => {
          this.socket?.connect();
        }, 2000);
      }
      
      // 디버깅: 글로벌 창 업데이트
      if (typeof window !== 'undefined') {
        // @ts-ignore
        if (!window._socketDebug) window._socketDebug = {};
        // @ts-ignore
        window._socketDebug.connected = false;
        // @ts-ignore
        window._socketDebug.disconnectReason = reason;
      }
    });
  }
  
  // Private method to bind the built-in socket events
  private _bindEvents() {
    if (!this.socket) return;
    
    // Basic Socket.io events
    this.socket.on('connect', () => {
      console.log('Socket connected:', this.socket?.id);
      this._triggerListeners('connect');
    });
    
    this.socket.on('disconnect', () => {
      console.log('Socket disconnected');
      this._triggerListeners('disconnect');
    });
    
    // Custom app events
    this.socket.on('new-message', (data) => {
      console.log('New message received via socket:', data);
      this._triggerListeners('new-message', data);
    });
    
    this.socket.on('thinking', (data) => {
      console.log('Thinking indicator:', data);
      this._triggerListeners('thinking', data);
    });
    
    // Auto dialogue events
    this.socket.on('auto-thinking', (data) => {
      console.log('🤖 [SocketClient] Auto-dialogue thinking event received:', JSON.stringify(data));
      
      // 명확한 로깅 - 이 시점에서 데이터 구조 확인
      if (data && data.npc_id) {
        console.log('🤖 [SocketClient] Auto-thinking NPC ID is:', data.npc_id);
      } else {
        console.warn('🤖 [SocketClient] Auto-thinking data is missing NPC ID:', data);
      }
      
      // 리스너에 데이터 전달 직전 로깅
      console.log('🤖 [SocketClient] About to trigger auto-thinking event listeners');
      this._triggerListeners('auto-thinking', data);
      console.log('🤖 [SocketClient] Finished triggering auto-thinking event listeners');
    });
    
    // npc-selected 이벤트 처리
    this.socket.on('npc-selected', (data) => {
      console.log('🎯 [SocketClient] NPC selected event received:', JSON.stringify(data));
      
      // 명확한 로깅 - 이 시점에서 데이터 구조 확인
      if (data && data.npc_id) {
        console.log('🎯 [SocketClient] Selected NPC ID is:', data.npc_id);
        if (data.npc_name) {
          console.log('🎯 [SocketClient] Selected NPC name is:', data.npc_name);
        }
      } else {
        console.warn('🎯 [SocketClient] NPC-selected data is missing NPC ID:', data);
      }
      
      // 리스너에 데이터 전달 직전 로깅
      console.log('🎯 [SocketClient] About to trigger npc-selected event listeners');
      this._triggerListeners('npc-selected', data);
      console.log('🎯 [SocketClient] Finished triggering npc-selected event listeners');
    });
    
    this.socket.on('auto-message-sent', (data) => {
      console.log('🤖 [SocketClient] Auto-dialogue message sent event received');
      
      // 리스너에 데이터 전달 직전 로깅
      console.log('🤖 [SocketClient] About to trigger auto-message-sent event listeners');
      this._triggerListeners('auto-message-sent', data);
      console.log('🤖 [SocketClient] Finished triggering auto-message-sent event listeners');
    });
    
    // Pong response for connection testing
    this.socket.on('pong', (data) => {
      const roundTripTime = Date.now() - data.time;
      console.log(`📡 PONG received! Round-trip time: ${roundTripTime}ms`);
      console.log(`📡 Server time: ${new Date(data.serverTime).toISOString()}`);
      
      // Show an alert for easy testing
      if (typeof window !== 'undefined') {
        window.alert(`Socket connection working! Round-trip time: ${roundTripTime}ms`);
      }
    });
    
    // 채팅방 참가자 이벤트 
    this.socket.on('user-joined', (data) => {
      console.log('User joined:', data);
      this._triggerListeners('user-joined', data);
    });
    
    this.socket.on('user-left', (data) => {
      console.log('User left:', data);
      this._triggerListeners('user-left', data);
    });
    
    this.socket.on('active-users', (data) => {
      console.log('Active users update:', data);
      this._triggerListeners('active-users', data);
    });
    
    this.socket.on('error', (data) => {
      console.error('Socket error:', data);
      this._triggerListeners('error', data);
    });
    
    // Room Created 이벤트 추가 - 새 채팅방이 만들어졌을 때
    this.socket.on('room-created', (data) => {
      console.log('🔊 SOCKET EVENT: room-created received', data);
      this._triggerListeners('room-created', data);
    });
  }
  
  /**
   * 특정 채팅방에 참여
   * @param roomId 채팅방 ID
   * @returns 성공 여부
   */
  joinRoom(roomId: number | string): boolean {
    if (!this.socket || !this.isConnected()) {
      console.error('Cannot join room: Socket not connected');
      return false;
    }
    
    // 항상 숫자로 변환하여 로깅 및 전송
    const normalizedId = Number(roomId);
    console.log(`SocketClient: Joining room ${roomId} (${typeof roomId}) -> ${normalizedId} (number)`);
    
    if (isNaN(normalizedId) || normalizedId <= 0) {
      console.error(`Invalid room ID: ${roomId}`);
      return false;
    }
    
    // 이미 참여한 방인지 확인
    if (this.rooms.includes(normalizedId)) {
      console.log(`Already in room: ${normalizedId}`);
      return true;
    }
    
    // 'join-room' 이벤트로 수정 - 서버가 이 이벤트를 기대하므로
    this.socket.emit('join-room', { roomId: normalizedId, username: this.username });
    this.rooms.push(normalizedId);
    
    return true;
  }

  /**
   * 특정 채팅방에서 나가기
   * @param roomId 채팅방 ID
   * @returns 성공 여부
   */
  leaveRoom(roomId: number | string): boolean {
    if (!this.socket || !this.isConnected()) {
      console.error('Cannot leave room: Socket not connected');
      return false;
    }
  
    // 항상 숫자로 변환하여 로깅 및 전송
    const normalizedId = Number(roomId);
    console.log(`SocketClient: Leaving room ${roomId} (${typeof roomId}) -> ${normalizedId} (number)`);
    
    if (isNaN(normalizedId) || normalizedId <= 0) {
      console.error(`Invalid room ID: ${roomId}`);
      return false;
    }
    
    // 참여한 방인지 확인
    const index = this.rooms.indexOf(normalizedId);
    if (index === -1) {
      console.log(`Not in room: ${normalizedId}`);
      return false;
    }
    
    this.socket.emit('leave-room', { roomId: normalizedId, username: this.username });
    this.rooms.splice(index, 1);
    
    return true;
  }
  
  // Send a message to a chat room
  public sendMessage(roomId: string | number, message: string, customMessageObj?: any, useRAG: boolean = false) {
    console.log('⚡️ socketClient.sendMessage 호출됨 - TRACE:', new Error().stack);
    console.log('⚡️ 전송 파라미터:', { roomId, messageText: message, useRAG });
    console.log('⚡️ Socket 객체 존재 여부:', !!this.socket);
    console.log('⚡️ Socket 연결 상태:', this.socket?.connected ? '연결됨' : '연결안됨');
    
    if (!this.socket) {
      console.error('❌ Socket 객체가 존재하지 않음 - Cannot send message');
      return false;
    }
    
    if (!this.socket.connected) {
      console.error('❌ Socket not connected - Cannot send message');
      return false;
    }
    
    try {
      console.log('📨 Socket 메시지 전송 시작 - 방:', roomId, '타입:', typeof roomId);
      
      // IMPORTANT: Convert roomId to number for consistency
      const roomIdNum = Number(roomId);
      if (isNaN(roomIdNum)) {
        console.error('❌ Invalid room ID:', roomId);
        return false;
      }
      
      console.log(`📨 Socket: Using normalized roomId: ${roomIdNum} (number)`);
      
      // Create a formatted message object - simplified for reliable transmission
      const messageObj = customMessageObj || {
        id: `socket-${Date.now()}`,
        text: message,
        sender: this.username,
        isUser: true,
        timestamp: new Date()  // Keep as Date object for type compatibility
      };
      
      // 인용 정보를 가진 AI 메시지인 경우 citations 필드 포함 유지
      if (customMessageObj && (customMessageObj.citations || customMessageObj.metadata?.citations)) {
        messageObj.citations = customMessageObj.citations || customMessageObj.metadata?.citations;
        console.log('📚 인용 정보가 포함된 메시지:', messageObj.citations);
      }
      
      console.log('📨 생성된 메시지 객체:', messageObj);
      
      // Emit the message object
      console.log('🔆 Emit 직전 - Socket 객체 존재 여부:', !!this.socket);
      console.log('🔆 Emit 직전 - Socket 연결 상태:', this.socket?.connected);
      console.log('🔆 Socket ID:', this.socket?.id);
      
      try {
        // 'send-message' 이벤트 사용
        console.log('⚡️ 실제 socket.emit 직전:', {
          eventName: 'send-message',
          payload: {
            roomId: roomIdNum,
            message: messageObj,
            useRAG
          }
        });
        
        // Get internal socket details for debugging
        console.log('⚡️ Socket 내부 상태:', {
          id: this.socket.id,
          connected: this.socket.connected,
          disconnected: this.socket.disconnected,
          transport: this.socket.io?.engine?.transport?.name
        });
        
        this.socket.emit('send-message', {
          roomId: roomIdNum,
          message: messageObj,
          useRAG: useRAG
        });
        console.log(`✅ 메시지 emit 완료 - 이벤트명: "send-message", 데이터:`, { roomId: roomIdNum, message: messageObj, useRAG });
      } catch (emitError) {
        console.error('🔥 EMIT ERROR:', emitError);
        throw emitError;
      }
      
      return true;
    } catch (error) {
      console.error('💥 메시지 전송 중 오류 발생:', error);
      return false;
    }
  }
  
  // Get active users in a room
  public getActiveUsers(roomId: string | number) {
    if (!this.socket?.connected) {
      console.error('Socket not connected');
      return;
    }
    
    this.socket.emit('get-active-users', roomId);
  }
  
  // Add an event listener
  public on(event: string, callback: Function) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    return this;
  }
  
  // Remove an event listener
  public off(event: string, callback: Function) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
    return this;
  }
  
  // Trigger all listeners for an event
  private _triggerListeners(event: string, ...args: any[]) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => {
        callback(...args);
      });
    }
  }
  
  // Disconnect the socket
  public disconnect() {
    this.socket?.disconnect();
    this.socket = null;
  }
  
  // Check if socket is connected
  public isConnected() {
    return this.socket?.connected || false;
  }
  
  // Get current username
  public getUsername() {
    return this.username;
  }
  
  // Set username
  public setUsername(username: string) {
    this.username = username;
    return this;
  }
  
  // Add method to register custom event handler
  public addEventHandler<T>(event: string, handler: EventHandler<T>): void {
    this.eventHandlers[event] = handler;
    console.log(`📝 Added custom event handler for ${event}`);
  }
  
  // Generic emit method for sending custom events
  public emit(event: string, data: any) {
    console.log(`🔄 Custom emit for event: ${event}`, data);
    
    if (!this.socket) {
      console.error('❌ Socket not initialized - Cannot emit event');
      return false;
    }
    
    if (!this.socket.connected) {
      console.error(`❌ Socket not connected - Cannot emit event: ${event}`);
      return false;
    }
    
    try {
      // Apply custom handler if exists
      let processedData = data;
      if (this.eventHandlers[event]) {
        try {
          processedData = this.eventHandlers[event](data);
          console.log(`✅ Applied custom handler for ${event}`);
        } catch (handlerError) {
          console.error(`❌ Error in custom handler for ${event}:`, handlerError);
        }
      }
      
      this.socket.emit(event, processedData);
      console.log(`✅ Emitted custom event: ${event}`, processedData);
      return true;
    } catch (error) {
      console.error(`❌ Error emitting event ${event}:`, error);
      return false;
    }
  }
  
  // Generate a random username
  public static generateRandomUsername() {
    return `User_${Math.floor(Math.random() * 10000)}`;
  }
  
  // Simple ping method to test socket communication
  public ping() {
    console.log('⚡ Sending ping to server...');
    if (!this.socket?.connected) {
      console.error('❌ Cannot ping: Socket not connected');
      return false;
    }
    
    try {
      this.socket.emit('ping', { time: Date.now(), username: this.username });
      console.log('✅ Ping sent successfully');
      return true;
    } catch (error) {
      console.error('❌ Error sending ping:', error);
      return false;
    }
  }
}

// Export as singleton
export const socketClient = new SocketClient();
export default socketClient;
export type { SocketClient }; 