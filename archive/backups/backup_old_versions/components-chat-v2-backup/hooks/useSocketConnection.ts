import { useEffect, useCallback, useRef } from 'react';
import { SocketEvents, TurnInfo } from '../types/debate.types';

interface UseSocketConnectionProps {
  roomId: string;
  username: string;
  onTurnUpdate?: (turnInfo: TurnInfo) => void;
  onNpcSelected?: (npcId: string) => void;
  onNewMessage?: (message: any) => void;
  onUserJoined?: (data: any) => void;
  onUserLeft?: (data: any) => void;
}

export function useSocketConnection({
  roomId,
  username,
  onTurnUpdate,
  onNpcSelected,
  onNewMessage,
  onUserJoined,
  onUserLeft,
}: UseSocketConnectionProps) {
  const socketRef = useRef<any>(null);
  const isInitializedRef = useRef(false);

  // 소켓 초기화
  const initializeSocket = useCallback(async () => {
    if (isInitializedRef.current) return;

    try {
      // 동적 import로 SSR 문제 방지
      const { default: socketClient } = await import('@/lib/socket/socketClient');
      
      const storedUsername = sessionStorage.getItem('chat_username') || username;
      await socketClient.init(storedUsername);
      
      socketRef.current = socketClient;
      isInitializedRef.current = true;

      // 방 참가
      console.log(`Socket: Joining room ${roomId}`);
      socketClient.joinRoom(roomId, storedUsername);

      return socketClient;
    } catch (error) {
      console.error('Error initializing socket:', error);
      return null;
    }
  }, [roomId, username]);

  // 이벤트 리스너 설정
  const setupEventListeners = useCallback((socketInstance: any) => {
    if (!socketInstance) return;

    // NPC 선택 이벤트
    const handleNpcSelected = (data: { npc_id: string }) => {
      console.log('NPC selected for response:', data.npc_id);
      onNpcSelected?.(data.npc_id);
    };

    // 차례 업데이트 이벤트 (커스텀 DOM 이벤트)
    const handleNextSpeakerUpdate = (event: CustomEvent) => {
      if (event.detail && typeof event.detail.is_user === 'boolean') {
        console.log('User turn detected from event!', event.detail);
        onTurnUpdate?.({
          isUserTurn: event.detail.is_user,
          nextSpeaker: event.detail,
        });
      }
    };

    // 새 메시지 이벤트
    const handleNewMessage = (data: { message: any; roomId: string }) => {
      console.log('New message received from socket:', data);
      onNewMessage?.(data.message);
    };

    // 소켓 이벤트 리스너 등록
    socketInstance.on('npc-selected', handleNpcSelected);
    socketInstance.on('new-message', handleNewMessage);
    
    // DOM 이벤트 리스너 등록
    document.addEventListener('next-speaker-update', handleNextSpeakerUpdate as EventListener);

    // 정리 함수 반환
    return () => {
      socketInstance.off('npc-selected', handleNpcSelected);
      socketInstance.off('new-message', handleNewMessage);
      document.removeEventListener('next-speaker-update', handleNextSpeakerUpdate as EventListener);
    };
  }, [onNpcSelected, onTurnUpdate, onNewMessage]);

  // 소켓 정리
  const cleanupSocket = useCallback(() => {
    if (socketRef.current && roomId) {
      const storedUsername = sessionStorage.getItem('chat_username') || username;
      console.log(`Socket: Leaving room ${roomId}`);
      socketRef.current.leaveRoom(roomId, storedUsername);
    }
    isInitializedRef.current = false;
  }, [roomId, username]);

  // 메시지 전송
  const emitMessage = useCallback((eventName: string, data: any) => {
    if (socketRef.current) {
      socketRef.current.emit(eventName, data);
    } else {
      console.warn('Socket not initialized, cannot emit message');
    }
  }, []);

  // 연결 상태 확인
  const isConnected = useCallback((): boolean => {
    return socketRef.current?.isConnected?.() || false;
  }, []);

  // 소켓 초기화 및 정리
  useEffect(() => {
    if (!roomId) return;

    let cleanupListeners: (() => void) | undefined;

    const init = async () => {
      const socketInstance = await initializeSocket();
      if (socketInstance) {
        cleanupListeners = setupEventListeners(socketInstance);
      }
    };

    init();

    return () => {
      cleanupListeners?.();
      cleanupSocket();
    };
  }, [roomId, initializeSocket, setupEventListeners, cleanupSocket]);

  return {
    socket: socketRef.current,
    isConnected: isConnected(),
    emitMessage,
    cleanupSocket,
  };
} 