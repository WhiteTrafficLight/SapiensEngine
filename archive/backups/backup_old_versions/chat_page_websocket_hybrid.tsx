'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ChatUI from '@/components/chat/ChatUI';
import CircularChatUI from '@/components/chat/CircularChatUI';
import DebateChatUI from '@/components/chat/DebateChatUI';
import chatService, { ChatRoom, ChatMessage } from '@/lib/ai/chatService';

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // 컴포넌트 초기화 시 한 번만 id 값을 추출하고 null 체크
  const chatIdParam = searchParams ? searchParams.get('id') : null;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatData, setChatData] = useState<ChatRoom | null>(null);
  const [isGeneratingResponse, setIsGeneratingResponse] = useState(false);
  
  // WebSocket 연결 관리
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // WebSocket 연결 함수
  const connectWebSocket = (roomId: string) => {
    const wsUrl = `ws://localhost:8000/api/chat/ws/${roomId}`;
    console.log(`🔌 WebSocket 연결 시도: ${wsUrl}`);
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log(`✅ WebSocket 연결 성공: ${roomId}`);
        console.log(`🔌 WebSocket 상태: OPEN (readyState: ${ws.readyState})`);
        wsRef.current = ws;
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log(`📥 WebSocket 메시지 수신:`, data);
          console.log(`📥 [상세] event_type: ${data.event_type}, speaker: ${data.speaker}, stage: ${data.stage}`);
          console.log(`📥 [메시지 내용] ${data.message ? data.message.substring(0, 100) + '...' : 'No message content'}`);
          
          if (data.event_type === 'new_message') {
            console.log(`✅ 새 메시지 데이터 처리 시작 - 발신자: ${data.speaker}`);
            
            // 실시간 메시지를 채팅에 추가
            const newMessage: ChatMessage = {
              id: data.id || `ws-${Date.now()}`,
              text: data.message || data.content || '',
              sender: data.speaker,
              isUser: false,
              timestamp: new Date(data.timestamp || Date.now()),
              isSystemMessage: data.speaker === 'moderator' || data.message_type === 'moderator',
              role: data.speaker === 'moderator' ? 'moderator' : 'participant'
            };
            
            console.log(`📝 생성된 메시지 객체:`, {
              id: newMessage.id,
              text: newMessage.text.substring(0, 50) + '...',
              sender: newMessage.sender,
              role: newMessage.role
            });
            
            // 임시 대기 메시지 교체 및 새 메시지 추가
            setChatData(prevData => {
              if (!prevData) {
                console.log('❌ prevData가 없음 - 메시지 추가 불가');
                return prevData;
              }
              
              const updatedData = { ...prevData };
              
              // 임시 대기 메시지 제거
              if (data.speaker === 'moderator' || data.speaker === 'Moderator') {
                const beforeCount = updatedData.messages?.length || 0;
                updatedData.messages = updatedData.messages?.filter(msg => 
                  !msg.id.startsWith('temp-waiting-')
                ) || [];
                const afterCount = updatedData.messages.length;
                console.log(`🔄 임시 대기 메시지 제거: ${beforeCount} -> ${afterCount}`);
              }
              
              // 중복 메시지 확인
              const isDuplicate = updatedData.messages?.some(msg => 
                msg.text === newMessage.text && msg.sender === newMessage.sender
              );
              
              if (!isDuplicate) {
                const beforeCount = updatedData.messages?.length || 0;
                updatedData.messages = [...(updatedData.messages || []), newMessage];
                console.log(`✅ 메시지 추가 완료: ${beforeCount + 1}개 메시지 (${data.speaker})`);
                console.log(`📄 메시지 내용: "${newMessage.text.substring(0, 100)}..."`);
                
                // 💾 DB에 메시지 저장
                const saveMessageToDB = async () => {
                  try {
                    console.log(`💾 DB 저장 시작: 방 ${roomId}, 메시지 ID ${newMessage.id}`);
                    
                    const response = await fetch(`/api/rooms?id=${roomId}`, {
                      method: 'PUT',
                      headers: {
                        'Content-Type': 'application/json',
                      },
                      body: JSON.stringify({
                        message: newMessage
                      }),
                    });

                    if (response.ok) {
                      const result = await response.json();
                      console.log(`✅ DB 저장 성공: 방 ${roomId}, 메시지 "${newMessage.text.substring(0, 50)}..."`);
                    } else {
                      const errorData = await response.json();
                      console.error(`❌ DB 저장 실패: ${response.status}`, errorData);
                    }
                  } catch (error) {
                    console.error(`❌ DB 저장 중 오류: 방 ${roomId}`, error);
                  }
                };
                
                // 비동기로 DB 저장 (UI 블로킹 방지)
                saveMessageToDB();
              } else {
                console.log(`⚠️ 중복 메시지 무시: ${data.speaker}`);
              }
              
              return updatedData;
            });
          } else {
            console.log(`📥 기타 이벤트 타입: ${data.event_type}`);
          }
        } catch (error) {
          console.error('❌ WebSocket 메시지 파싱 오류:', error);
          console.error('❌ 원본 데이터:', event.data);
        }
      };
      
      ws.onerror = (error) => {
        console.error(`❌ WebSocket 오류:`, error);
        console.error(`🔌 WebSocket 상태: ERROR (readyState: ${ws.readyState})`);
      };
      
      ws.onclose = (event) => {
        console.log(`🔌 WebSocket 연결 종료: 코드=${event.code}, 이유="${event.reason}"`);
        console.log(`🔌 정상 종료 여부: ${event.wasClean ? 'YES' : 'NO'}`);
        wsRef.current = null;
        
        // 비정상 종료시 재연결 시도
        if (event.code !== 1000 && event.code !== 1001) {
          console.log('🔄 5초 후 WebSocket 재연결 시도...');
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`🔄 재연결 시도 중: ${roomId}`);
            connectWebSocket(roomId);
          }, 5000);
        }
      };
      
    } catch (error) {
      console.error('❌ WebSocket 연결 생성 실패:', error);
    }
  };

  // WebSocket 연결 해제 함수
  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      console.log('🔌 WebSocket 연결 해제');
      wsRef.current.close(1000, 'Component unmounting');
      wsRef.current = null;
    }
  };

  // 페이지 진입 시 body 스타일 변경
  useEffect(() => {
    // 헤더를 숨기기 위한 클래스 추가
    document.body.classList.add('chat-page-open');
    
    // 페이지 나갈 때 스타일 복원 및 WebSocket 연결 해제
    return () => {
      document.body.classList.remove('chat-page-open');
      disconnectWebSocket();
    };
  }, []);

  // 채팅 데이터 로드 후 WebSocket 연결
  useEffect(() => {
    if (chatData && chatData.dialogueType === 'debate') {
      // debate_info에서 room_id를 찾거나 chatData.id를 사용
      const roomId = chatData.id.toString();
      console.log(`🎯 디베이트 모드 감지 - WebSocket 연결 시작: ${roomId}`);
      connectWebSocket(roomId);
    }
    
    return () => {
      disconnectWebSocket();
    };
  }, [chatData]);

  useEffect(() => {
    // 마운트 시 상태 초기화
    setLoading(true);
    setError(null);
    setChatData(null);
    
    if (!chatIdParam) {
      setError('No chat ID provided');
      setLoading(false);
      return;
    }

    console.log('Chat page received ID:', chatIdParam, typeof chatIdParam);

    // Use string chatId instead of converting to number
    const chatId = chatIdParam;
    console.log('Using chat ID as string:', chatId, `(${typeof chatId})`);
    
    // Remove numeric validation since we now support string IDs
    if (!chatId || chatId.trim() === '') {
      console.error(`Invalid chat ID format: ${chatIdParam}`);
      setError('Invalid chat room ID format');
      setLoading(false);
      return;
    }

    const loadChatData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // URL의 chatId와 함께 실행되는 요청임을 명확히 로깅
        console.log(`🔍 CHAT PAGE: Fetching chat room with ID: ${chatId}, (type: ${typeof chatId})`);
        const room = await chatService.getChatRoomById(chatId);
        
        if (!room) {
          console.error('Room not found for ID:', chatId);
          setError('Chat room not found');
          return;
        }
        
        // ID 타입 및 일치 여부 확인
        console.log(`🔍 CHAT PAGE: Room returned with ID: ${room.id} (${typeof room.id})`);
        
        // 🔧 ID를 문자열로 정규화 (parseInt 제거)
        const roomId = String(room.id);
        const requestedChatId = String(chatId);
        
        if (roomId !== requestedChatId) {
          console.error(`ID mismatch: requested=${requestedChatId}, received=${roomId}`);
          setError('Incorrect chat room loaded');
          return;
        }
        
        // 🔧 ID를 명시적으로 문자열로 설정
        room.id = String(chatId);
        
        // 채팅방 메시지 상태 확인
        const messageCount = room.messages?.length || 0;
        console.log(`🔍 CHAT PAGE: Successfully loaded room #${room.id} (${room.title}) with ${messageCount} messages`);
        console.log(`🔍 CHAT PAGE: Dialog type: "${room.dialogueType || 'not set'}"`, room);
        
        if (messageCount > 0 && room.messages) {
          // 메시지 내용 간략히 로깅
          console.log(`🔍 CHAT PAGE: First message: "${room.messages[0].text.substring(0, 30)}..."`);
          if (messageCount > 1) {
            console.log(`🔍 CHAT PAGE: Last message: "${room.messages[messageCount-1].text.substring(0, 30)}..."`);
          }
        }
        
        // Check if room has any users (excluding NPCs)
        if (room.participants.users.length === 0) {
          // No users left in the chat room, redirect to open chat page
          console.log('🔍 CHAT PAGE: No users in room, redirecting to open chat');
          router.push('/open-chat');
          return;
        }
        
        // Ensure dialogueType is set (default to 'free' if not explicitly set in database)
        if (!room.dialogueType) {
          console.log('🔧 CHAT PAGE: Setting default dialogueType to "free"');
          room.dialogueType = 'free';
        }
        
        // 이전 상태와 완전히 다른 새 객체로 설정하여 상태 격리
        setChatData(JSON.parse(JSON.stringify(room)));
      } catch (error) {
        console.error('Failed to load chat:', error);
        setError('Failed to load chat data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    loadChatData();
  }, [chatIdParam, router]);

  const handleBackToOpenChat = () => {
    router.push('/open-chat');
  };

  // 사용자 역할 결정 헬퍼 함수
  const getUserRole = () => {
    if (!chatData) return 'neutral';
    
    console.log('⚡ 유저 역할 결정 - 분석 중', {
      roomData: chatData,
      proParticipants: chatData.pro || [],
      conParticipants: chatData.con || [],
      userInPro: chatData.pro?.some(id => id === 'User' || id === 'User123' || id === 'You'),
      userInCon: chatData.con?.some(id => id === 'User' || id === 'User123' || id === 'You')
    });
    
    // 명시적으로 pro 배열에 사용자가 있는지 확인
    if (chatData.pro?.some(id => id === 'User' || id === 'User123' || id === 'You')) {
      console.log('⚡ 유저는 PRO(찬성) 측입니다');
      return 'pro';
    }
    
    // 명시적으로 con 배열에 사용자가 있는지 확인
    if (chatData.con?.some(id => id === 'User' || id === 'User123' || id === 'You')) {
      console.log('⚡ 유저는 CON(반대) 측입니다');
      return 'con';
    }
    
    console.log('⚡ 유저 역할을 결정할 수 없습니다. neutral로 설정합니다.');
    return 'neutral';
  };

  // 메시지 전송 및 AI 응답 생성 함수
  const handleSendMessage = async (message: string) => {
    if (!chatData) return;
    
    try {
      // 디베이트 모드인지 확인
      const isDebateMode = chatData.dialogueType === 'debate';
      
      // 현재 사용자 역할 확인
      const currentUserRole = getUserRole();
      console.log(`💬 사용자 메시지 전송 시작 - 역할: ${currentUserRole}, 디베이트 모드: ${isDebateMode}`);
      
      // 사용자 메시지 객체 생성 - 모든 필수 필드 명시적으로 설정
      const userMessageObj = {
        id: `user-${Date.now()}`,
        text: message.trim(),
        sender: 'User',
        isUser: true,
        timestamp: new Date().toISOString(),
        role: currentUserRole
      };
      
      console.log(`📝 사용자 메시지 객체:`, userMessageObj);
      
      // 1. Next.js API를 통해 메시지 DB 저장 (중요: debate 모드여도 먼저 저장)
      try {
        console.log(`💾 Next.js API에 메시지 저장 시도...`);
        const saveResult = await chatService.sendMessage(chatData.id, message, userMessageObj);
        console.log(`✅ 메시지 저장 결과:`, saveResult);
      } catch (error) {
        console.error('❌ Next.js API 메시지 저장 실패:', error);
      }
      
      // 2. 디베이트 모드인 경우, Python API에게 메시지 처리 요청
      if (isDebateMode) {
        console.log('🔄 디베이트 API에 사용자 메시지 처리 요청...');
        
        // Python API URL 설정
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        
        try {
          // 메시지 처리 API 호출 - 사용자 역할 정보 포함
          console.log(`📤 Python API 요청: ${apiBaseUrl}/api/dialogue/${chatData.id}/process-message`, {
            message: message,
            user_id: 'User',
            role: currentUserRole
          });
          
          const processResponse = await fetch(`${apiBaseUrl}/api/dialogue/${chatData.id}/process-message`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              message: message,
              user_id: 'User', // 일관된 사용자 ID 사용
              role: currentUserRole // 사용자 역할 정보 추가
            })
          });
          
          if (processResponse.ok) {
            const processResult = await processResponse.json();
            console.log('✅ Debate API 처리 결과:', processResult);
            
            // 사용자 메시지 처리 후, 자동으로 다음 발언자 요청 (짧은 지연 후)
            setTimeout(() => {
              handleRequestNextMessage();
            }, 1000);
          } else {
            console.error('❌ Debate API 처리 오류:', processResponse.status);
            const errorText = await processResponse.text();
            console.error('오류 내용:', errorText);
            
            // 오류가 발생해도 다음 발언자 요청을 시도
            setTimeout(() => {
              handleRequestNextMessage();
            }, 1000);
          }
        } catch (error) {
          console.error('❌ Debate API 호출 오류:', error);
        }
      }
      
      // 항상 UI 상태 업데이트
      setIsGeneratingResponse(true);
      
      // 채팅 목록 새로고침
      const updatedRoom = await chatService.getChatRoomById(chatData.id);
      if (updatedRoom) {
        setChatData(updatedRoom);
      }
    } catch (error) {
      console.error('❌ 메시지 처리 중 예외 발생:', error);
    } finally {
      // 처리 완료 상태로 변경
      setTimeout(() => {
      setIsGeneratingResponse(false);
      }, 500);
    }
  };

  // 채팅룸 새로고침 함수
  const handleRefreshChat = async () => {
    if (!chatData) return;
    
    setLoading(true);
    try {
      const refreshedRoom = await chatService.getChatRoomById(chatData.id);
      if (refreshedRoom) {
        setChatData(JSON.parse(JSON.stringify(refreshedRoom)));
      }
    } catch (error) {
      console.error('Failed to refresh chat:', error);
    } finally {
      setLoading(false);
    }
  };

  // Debate 모드에서 다음 메시지 요청 함수
  const handleRequestNextMessage = async () => {
    if (!chatData || chatData.dialogueType !== 'debate') return;
    
    try {
      // 응답 생성 중 상태 표시
      setIsGeneratingResponse(true);
      
      console.log('🔄 Requesting next debate message for room:', chatData.id);
      
      // Socket.io 클라이언트를 통한 요청
      const socketModule = await import('@/lib/socket/socketClient');
      await socketModule.default.init();
      
      // Socket 연결 확인
      if (!socketModule.default.isConnected()) {
        console.warn('Socket not connected, attempting to initialize...');
        await socketModule.default.init();
        
        if (!socketModule.default.isConnected()) {
          throw new Error('Failed to establish socket connection');
        }
      }
      
      // 1. 방 입장 확인
      const roomId = String(chatData.id);
      const storedUsername = sessionStorage.getItem('chat_username') || 'User';
      socketModule.default.joinRoom(roomId, storedUsername);
      
      // 이벤트 리스너 설정 - 다음 발언자 업데이트 수신
      socketModule.default.on('next-speaker-update', (data: { roomId: string, nextSpeaker: any }) => {
        console.log('Next speaker update from socket:', data);
        if (data.roomId === roomId && data.nextSpeaker) {
          // 전역 이벤트로 발행하여 DebateChatUI에서 감지하도록 함
          window.dispatchEvent(new CustomEvent('next-speaker-updated', { 
            detail: data.nextSpeaker 
          }));
          
          // 사용자 차례인 경우 자동 응답 생성하지 않음
          if (data.nextSpeaker.is_user) {
            console.log('👤 User is the next speaker - waiting for input');
            setIsGeneratingResponse(false);
            return;
          }
        }
      });
      
      // 새로운 메시지를 위한 이벤트 리스너 추가
      socketModule.default.on('new-message', (data: { roomId: string, message: ChatMessage }) => {
        console.log('New message received from socket:', data);
        if (data.roomId === roomId && data.message) {
          console.log('Adding new message to chatData state:', data.message);
          if (chatData) {
            // 기존 메시지 배열에 새 메시지 추가
            const updatedMessages = [...(chatData.messages || []), data.message];
            // 채팅방 데이터 업데이트
            setChatData(prevData => {
              if (!prevData) return null;
              return {
                ...prevData,
                messages: updatedMessages
              };
            });
          }
        }
      });
      
      // Python API URL 설정
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // 2. 디베이트 다음 메시지 요청 (백엔드 API 직접 호출)
      const response = await fetch(`${apiBaseUrl}/api/dialogue/${roomId}/next-speaker`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to request next debate message: ${response.status}`);
      }
      
      const nextSpeakerData = await response.json();
      console.log('Next speaker data:', nextSpeakerData);
      
      // 응답할 NPC ID 확인 - speaker_id 속성 사용 (API 반환 값과 일치)
      const speakerId = nextSpeakerData.speaker_id;
      if (!speakerId) {
        throw new Error('No next speaker returned from API');
      }
      
      console.log(`Next speaker determined: ${speakerId} (${nextSpeakerData.role || 'unknown role'})`);
      console.log(`Is user turn: ${nextSpeakerData.is_user}`);
      
      // 다음 발언자 정보를 localStorage에 저장 (UI에서 사용자 차례를 감지하는 데 활용)
      window.localStorage.setItem('lastNextSpeakerData', JSON.stringify(nextSpeakerData));
      
      // 사용자에게 차례 알림을 위한 전역 이벤트 발행
      window.dispatchEvent(new CustomEvent('next-speaker-updated', { 
        detail: nextSpeakerData 
      }));
      
      // NPC 선택 이벤트 발송
      socketModule.default.emit('npc-selected', {
        roomId: roomId,
        npcId: speakerId
      });
      
      // 사용자 ID 확인 (API 응답의 is_user 플래그 사용)
      const isUserNextSpeaker = nextSpeakerData.is_user === true;
      
      // 사용자가 다음 발언자이면 AI 응답 생성 건너뛰기
      if (isUserNextSpeaker) {
        console.log('👤 User is the next speaker, waiting for user input...');
        // 사용자 차례이므로 상태 업데이트만 하고 함수 종료
        setIsGeneratingResponse(false);
        return;
      }
      
      // 3. 다음 발언자 메시지 생성 요청 (사용자가 아닌 경우에만)
      const generateResponse = await fetch(`${apiBaseUrl}/api/dialogue/${roomId}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          npc_id: speakerId
        })
      });
      
      if (!generateResponse.ok) {
        throw new Error(`Failed to generate next debate message: ${generateResponse.status}`);
      }
      
      const messageData = await generateResponse.json();
      console.log('Generated message:', messageData);
      
      // 4. 생성된 메시지를 DB에 저장
      if (messageData && messageData.response_text) {
        // NextJS API에 메시지 저장 요청
        const saveMessageUrl = `/api/messages`;
        const messageToSave = {
          id: `ai-${Date.now()}`,
          text: messageData.response_text,
          sender: speakerId,
          isUser: false,
          timestamp: new Date().toISOString(),
          role: nextSpeakerData.role  // 역할 정보 추가
        };
        
        console.log('Saving message to database:', messageToSave);
        
        // API 요청 형식에 맞게 roomId와 message를 별도로 구성
        const saveResponse = await fetch(saveMessageUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            roomId: roomId,
            message: messageToSave
          })
        });
        
        if (!saveResponse.ok) {
          console.error('Failed to save message to database:', await saveResponse.text());
        } else {
          console.log('Message saved to database successfully');
          
          // UI에 직접 메시지 추가 (Socket 업데이트를 기다리지 않고 즉시 반영)
          if (chatData) {
            setChatData(prevData => {
              if (!prevData) return null;
              // 이미 동일한 ID의 메시지가 있는지 확인
              const messageExists = prevData.messages?.some(msg => msg.id === messageToSave.id);
              if (messageExists) {
                return prevData; // 이미 존재하면 상태 변경 없음
              }
              
              // ChatMessage 타입에 맞게 변환
              const newMessage: ChatMessage = {
                id: messageToSave.id,
                text: messageToSave.text,
                sender: messageToSave.sender,
                isUser: messageToSave.isUser,
                timestamp: new Date(messageToSave.timestamp), // string을 Date 객체로 변환
                role: messageToSave.role
              };
              
              // 새 메시지 추가
              return {
                ...prevData,
                messages: [...(prevData.messages || []), newMessage]
              };
            });
          }
        }
      }
      
    } catch (error) {
      console.error('Failed to request next debate message:', error);
    } finally {
      setIsGeneratingResponse(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 w-screen h-screen bg-white">
      {loading ? (
        <div className="flex h-full justify-center items-center">
          <div className="animate-pulse flex flex-col items-center">
            <div className="h-8 w-48 bg-gray-200 rounded mb-4"></div>
            <div className="h-4 w-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      ) : error ? (
        <div className="flex h-full justify-center items-center flex-col">
          <p className="text-xl text-gray-500 mb-4">{error}</p>
          <button 
            onClick={handleBackToOpenChat}
            className="px-4 py-2 bg-black text-white rounded-md"
          >
            Back to Open Chat
          </button>
        </div>
      ) : chatData ? (
        chatData.dialogueType === 'free' || !chatData.dialogueType ? (
          <CircularChatUI
            chatId={String(chatData.id)}
            chatTitle={chatData.title}
            participants={chatData.participants}
            initialMessages={chatData.messages || []}
            onBack={() => router.push('/open-chat')}
          />
        ) : chatData.dialogueType === 'debate' ? (
          <DebateChatUI
            room={{
              ...chatData,
              id: String(chatData.id)
            }}
            messages={chatData.messages || []}
            npcDetails={chatData.npcDetails || []}
            onSendMessage={handleSendMessage}
            onRefresh={handleRefreshChat}
            isLoading={loading}
            isGeneratingResponse={isGeneratingResponse}
            username="You"
            onEndChat={() => router.push('/open-chat')}
            userRole={
              // 사용자 역할 확인 (pro, con, neutral)
              chatData.pro?.includes('You') || chatData.pro?.includes('User123') ? 'pro' :
              chatData.con?.includes('You') || chatData.con?.includes('User123') ? 'con' :
              'neutral'
            }
            onRequestNextMessage={handleRequestNextMessage}
          />
        ) : (
        <ChatUI 
          chatId={String(chatData.id)}
          chatTitle={chatData.title}
          participants={chatData.participants}
          initialMessages={chatData.messages || []}
          onBack={() => router.push('/open-chat')}
        />
        )
      ) : (
        <div className="flex h-full justify-center items-center">
          <p className="text-xl text-gray-500">Chat not found</p>
        </div>
      )}
      
      {/* 스타일 추가 */}
      <style jsx global>{`
        /* 채팅 페이지에서 헤더 숨기기 */
        body.chat-page-open header {
          display: none !important;
        }
        
        /* 채팅 페이지가 열렸을 때 body 스크롤 방지 */
        body.chat-page-open {
          overflow: hidden;
        }
      `}</style>
    </div>
  );
} 