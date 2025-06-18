'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import DebateChatContainer from '@/components/chat/v2/DebateChatContainer';
import { chatService, ChatRoom, ChatMessage } from '@/lib/ai/chatService';

export default function ChatPageV2() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chatIdParam = searchParams ? searchParams.get('id') : null;
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatData, setChatData] = useState<ChatRoom | null>(null);
  const [isGeneratingResponse, setIsGeneratingResponse] = useState(false);
  const [socketClient, setSocketClient] = useState<any>(null);
  const [username, setUsername] = useState<string>('');
  const [typingMessageIds, setTypingMessageIds] = useState<Set<string>>(new Set());
  const [waitingForUserInput, setWaitingForUserInput] = useState(false);
  const [currentUserTurn, setCurrentUserTurn] = useState<{speaker_id: string, role: string} | null>(null);

  // 타이핑 완료 핸들러
  const handleTypingComplete = (messageId: string) => {
    setTypingMessageIds(prev => {
      const newSet = new Set(prev);
      newSet.delete(messageId);
      return newSet;
    });
  };

  // 사용자 정보 로드
  useEffect(() => {
    const loadUserInfo = async () => {
      try {
        const response = await fetch('/api/user/profile');
        if (response.ok) {
          const userData = await response.json();
          const userDisplayName = userData.username || userData.name || `User_${Math.floor(Math.random() * 10000)}`;
          setUsername(userDisplayName);
          sessionStorage.setItem('chat_username', userDisplayName);
          console.log('✅ V2: 사용자 정보 로드됨:', userDisplayName);
        } else {
          const storedUsername = sessionStorage.getItem('chat_username') || `User_${Math.floor(Math.random() * 10000)}`;
          setUsername(storedUsername);
          sessionStorage.setItem('chat_username', storedUsername);
        }
      } catch (error) {
        console.error('V2: 사용자 정보 로드 실패:', error);
        const fallbackUsername = `User_${Math.floor(Math.random() * 10000)}`;
        setUsername(fallbackUsername);
        sessionStorage.setItem('chat_username', fallbackUsername);
      }
    };
    
    loadUserInfo();
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setChatData(null);
    
    if (!chatIdParam) {
      setError('No chat ID provided');
      setLoading(false);
      return;
    }

    const chatId = chatIdParam;
    
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
        
        console.log(`🔍 CHAT PAGE V2: Fetching chat room with ID: ${chatId}`);
        const room = await chatService.getChatRoomById(chatId);
        
        if (!room) {
          console.error('Room not found for ID:', chatId);
          setError('Chat room not found');
          return;
        }
        
        console.log(`🔍 CHAT PAGE V2: Successfully loaded room #${room.id} (${room.title})`);
        
        // Ensure dialogueType is set
        if (!room.dialogueType) {
          room.dialogueType = 'free';
        }
        
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

  // Socket.IO 연결 및 실시간 메시지 수신 설정
  useEffect(() => {
    let socketInstance: any = null;

    const initializeSocket = async () => {
      if (!chatData?.id || !username) return;

      try {
        // socketClient 인스턴스 임포트 
        const socketClient = (await import('@/lib/socket/socketClient')).default;
        socketInstance = socketClient;
        await socketInstance.init(username);
        
        // 방에 참가 (username 전달)
        const roomId = String(chatData.id);
        socketInstance.joinRoom(roomId, username);
        
        // new-message 이벤트 리스너 설정
        socketInstance.on('new-message', async (data: { roomId: string, message: ChatMessage }) => {
          console.log('🎯 [V2] 소켓 이벤트 수신: new-message');
          console.log('🎯 [V2] 수신 데이터:', JSON.stringify(data).substring(0, 300));
          console.log('🎯 [V2] 현재 방 ID:', String(chatData.id));
          console.log('🎯 [V2] 수신된 방 ID:', String(data.roomId));
          
          // 현재 방의 메시지인지 확인
          const currentRoomId = String(chatData.id);
          const receivedRoomId = String(data.roomId);
          
          if (currentRoomId === receivedRoomId && data.message) {
            console.log('✅ [V2] 방 ID 일치! 메시지를 DB에 저장 후 UI에 업데이트');
            console.log('✅ [V2] 메시지 내용:', data.message.text?.substring(0, 100));
            console.log('✅ [V2] 이벤트 타입:', data.message.metadata?.event_type);
            
            // 완성된 메시지인지 확인
            const isCompleteMessage = data.message.metadata?.event_type === 'debate_message_complete';
            const isUserMessage = data.message.isUser === true;
            
            try {
              // 1. DB에 메시지 저장 (완성된 AI 메시지 또는 사용자 메시지)
              if (isCompleteMessage || isUserMessage) {
                console.log('💾 [V2] 메시지 DB 저장 시작...', isUserMessage ? '(사용자 메시지)' : '(AI 메시지)');
                const saveResponse = await fetch('/api/messages', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                  },
                  body: JSON.stringify({
                    roomId: currentRoomId,
                    message: {
                      ...data.message,
                      timestamp: data.message.timestamp || new Date().toISOString()
                    }
                  }),
                });
                
                if (saveResponse.ok) {
                  console.log('✅ [V2] DB 저장 성공!');
                } else {
                  const errorData = await saveResponse.json();
                  console.error('❌ [V2] DB 저장 실패:', errorData);
                }
              }
              
              // 2. UI 업데이트
              setChatData(prev => {
                if (!prev) return prev;
                
                // 완성된 메시지인 경우 임시 생성 중 메시지를 교체
                if (isCompleteMessage) {
                  console.log('🔄 [V2] 임시 메시지를 완성된 메시지로 교체');
                  
                  // 같은 발언자의 생성 중인 임시 메시지 찾기
                  const messagesCopy = [...(prev.messages || [])];
                  const tempMessageIndex = messagesCopy.findIndex(msg => 
                    msg.isGenerating && msg.sender === data.message.sender
                  );
                  
                  if (tempMessageIndex >= 0) {
                    // 임시 메시지를 완성된 메시지로 교체
                    const completeMessage = {
                      ...data.message,
                      skipAnimation: false,  // 완성된 메시지는 타이핑 애니메이션 적용
                      // metadata에서 RAG 정보 추출
                      rag_used: data.message.metadata?.rag_used || false,
                      rag_source_count: data.message.metadata?.rag_source_count || 0,
                      rag_sources: data.message.metadata?.rag_sources || []
                    };
                    messagesCopy[tempMessageIndex] = completeMessage;
                    console.log('✅ [V2] 임시 메시지 교체 완료');
                    console.log('🔍 [V2] RAG 정보:', {
                      rag_used: completeMessage.rag_used,
                      rag_source_count: completeMessage.rag_source_count,
                      rag_sources_length: completeMessage.rag_sources?.length || 0
                    });
                    
                    // 타이핑 애니메이션 시작을 위해 typingMessageIds에 추가
                    setTimeout(() => {
                      setTypingMessageIds(prev => new Set([...prev, completeMessage.id]));
                    }, 100);
                  } else {
                    // 임시 메시지가 없으면 새로 추가
                    console.log('⚠️ [V2] 임시 메시지를 찾을 수 없어 새로 추가');
                    const newMessage = {
                      ...data.message,
                      skipAnimation: false,
                      // metadata에서 RAG 정보 추출
                      rag_used: data.message.metadata?.rag_used || false,
                      rag_source_count: data.message.metadata?.rag_source_count || 0,
                      rag_sources: data.message.metadata?.rag_sources || []
                    };
                    
                    console.log('🔍 [V2] 일반 메시지 RAG 정보:', {
                      rag_used: newMessage.rag_used,
                      rag_source_count: newMessage.rag_source_count,
                      rag_sources_length: newMessage.rag_sources?.length || 0
                    });
                    
                    messagesCopy.push(newMessage);
                  }
                  
                  return {
                    ...prev,
                    messages: messagesCopy
                  };
                } else {
                  // 일반 메시지인 경우 기존 로직 사용
                  console.log('🔄 [V2] 일반 메시지 추가');
                  const newMessage = {
                    ...data.message,
                    skipAnimation: false,
                    // metadata에서 RAG 정보 추출
                    rag_used: data.message.metadata?.rag_used || false,
                    rag_source_count: data.message.metadata?.rag_source_count || 0,
                    rag_sources: data.message.metadata?.rag_sources || []
                  };
                  
                  console.log('🔍 [V2] 일반 메시지 RAG 정보:', {
                    rag_used: newMessage.rag_used,
                    rag_source_count: newMessage.rag_source_count,
                    rag_sources_length: newMessage.rag_sources?.length || 0
                  });
                  
                  return {
                    ...prev,
                    messages: [...(prev.messages || []), newMessage]
                  };
                }
              });
              
            } catch (error) {
              console.error('❌ [V2] 메시지 처리 중 오류:', error);
            }
            
          } else {
            console.log('❌ [V2] 방 ID 불일치 또는 메시지 없음');
            console.log('❌ [V2] 현재 방:', currentRoomId, '수신 방:', receivedRoomId, '메시지 존재:', !!data.message);
          }
        });
        
        // 추가 디버그 이벤트들
        socketInstance.on('connect', () => {
          console.log('🔗 [V2] Socket 연결됨:', socketInstance.getSocket()?.id);
        });
        
        socketInstance.on('disconnect', () => {
          console.log('❌ [V2] Socket 연결 해제됨');
        });
        
        // 모든 이벤트 캐치
        socketInstance.getSocket()?.onAny((eventName: string, ...args: any[]) => {
          console.log(`🎧 [V2] 받은 이벤트: ${eventName}`, args);
        });
        
        setSocketClient(socketInstance);
        console.log('V2: Socket.IO 연결 완료');
        
      } catch (error) {
        console.error('V2: Socket.IO 연결 실패:', error);
      }
    };

    if (chatData?.id) {
      initializeSocket();
    }

    return () => {
      if (socketInstance) {
        if (chatData?.id && username) {
          const roomId = String(chatData.id);
          socketInstance.leaveRoom(roomId, username);
        }
        socketInstance.disconnect();
      }
    };
  }, [chatData?.id, username]);

  const handleBackToOpenChat = () => {
    router.push('/open-chat');
  };

  const handleSendMessage = async (message: string) => {
    if (!chatData) return;
    
    try {
      console.log(`💬 V2: User message sent: ${message}`);
      
      // 간단한 메시지 전송 (기존 로직 단순화)
      const result = await chatService.sendMessage(chatData.id, message, {
        id: `user-${Date.now()}`,
        text: message.trim(),
        sender: username || 'User',
        isUser: true,
        timestamp: new Date().toISOString(),
        role: 'user'
      });
      
      console.log(`✅ V2: Message sent successfully:`, result);
      
      // 채팅 데이터 새로고침
      const updatedRoom = await chatService.getChatRoomById(chatData.id);
      if (updatedRoom) {
        setChatData(updatedRoom);
      }
    } catch (error) {
      console.error('❌ V2: Message sending failed:', error);
    }
  };

  const handleRefreshChat = async () => {
    if (!chatData) return;
    
    console.log('🔄 [V2] handleRefreshChat 호출됨');
    console.log('🔄 [V2] 새로고침 전 메시지 수:', chatData.messages?.length || 0);
    
    setLoading(true);
    try {
      const refreshedRoom = await chatService.getChatRoomById(chatData.id);
      if (refreshedRoom) {
        console.log('🔄 [V2] 서버에서 가져온 메시지 수:', refreshedRoom.messages?.length || 0);
        setChatData(JSON.parse(JSON.stringify(refreshedRoom)));
        console.log('🔄 [V2] 새로고침 완료 - 데이터 교체됨');
      }
    } catch (error) {
      console.error('Failed to refresh chat:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRequestNextMessage = async () => {
    if (!chatData) return;
    
    try {
      setIsGeneratingResponse(true);
      console.log('🔄 V2: Requesting next debate message for room:', chatData.id);
      
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const roomId = String(chatData.id);
      
      const response = await fetch(`${apiBaseUrl}/api/chat/debate/${roomId}/next-message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Next 메시지 요청 실패');
      }
      
      const data = await response.json();
      console.log('📋 Next speaker info received:', data);
      
      if (data.status === 'success') {
        // 백엔드에서 next_speaker 정보가 있는 경우
        if (data.next_speaker) {
          const { speaker_id, role, is_user } = data.next_speaker;
          
          console.log('🎯 Next speaker details:', { speaker_id, role, is_user });
          console.log('🎯 Current username:', username);
          
          if (is_user === true) {
            console.log('👤 USER TURN CONFIRMED - activating input');
            console.log('👤 Speaker ID:', speaker_id, 'Role:', role);
            
            // 사용자 차례 상태 설정 (테스트 파일과 동일한 로직)
            setCurrentUserTurn({ speaker_id, role });
            setWaitingForUserInput(true);
            setIsGeneratingResponse(false);
            
            // 사용자에게 명확한 알림 (테스트 파일과 유사한 메시지)
            const roleText = role === 'pro' ? 'Pro' : role === 'con' ? 'Con' : role;
            const message = `It's your turn to speak as the ${roleText} side. Please enter your opinion.`;
            
            console.log('👤 Showing user turn alert:', message);
            alert(message);
            
            // 입력창 포커스를 위한 약간의 지연
            setTimeout(() => {
              console.log('👤 Attempting to focus input');
              if (document.querySelector('.debate-input-field')) {
                (document.querySelector('.debate-input-field') as HTMLTextAreaElement)?.focus();
              }
            }, 500);
            
            return; // 사용자 차례인 경우 여기서 종료
          } else {
            console.log('🤖 Not user turn - is_user is false');
          }
        } else {
          console.log('⚠️ No next_speaker data in success response');
        }
        
        // AI 차례인 경우 (기존 로직은 generating 상태에서 처리)
        console.log('🤖 Success response but not user turn - treating as AI turn');
        setIsGeneratingResponse(false);
      } else if (data.status === 'generating') {
        // 백엔드에서 "generating" 상태를 반환한 경우 처리
        console.log('🤖 AI generating message - showing thinking animation');
        
        const tempMessage: ChatMessage = {
          id: `temp-waiting-${Date.now()}`,
          text: 'Generating message...',
          sender: data.speaker_id,
          isUser: false,
          timestamp: new Date(),
          isGenerating: true,
          skipAnimation: true
        };
        
        setChatData(prev => {
          if (!prev) return prev;
          return {
            ...prev,
            messages: [...(prev.messages || []), tempMessage]
          };
        });
        
        console.log('🎭 Temporary message added, waiting for AI response via Socket.IO');
        
      } else if (data.status === 'completed') {
        console.log('🏁 Debate completed');
        alert('The debate has been completed!');
        setIsGeneratingResponse(false);
      } else {
        throw new Error(data.message || 'Unknown response status');
      }
      
    } catch (error) {
      console.error('❌ Error requesting next message:', error);
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      alert(`Error occurred while requesting next message: ${errorMessage}`);
      setIsGeneratingResponse(false);
    }
  };

  // 사용자 메시지 처리 함수 (테스트 파일과 동일한 로직)
  const handleProcessUserMessage = async (message: string) => {
    if (!currentUserTurn || !chatData) {
      console.error('❌ Cannot process user message - missing currentUserTurn or chatData');
      return;
    }
    
    try {
      console.log('🎯 Processing user message:', message);
      console.log('🎯 Current user turn:', currentUserTurn);
      console.log('🎯 Username:', username);
      
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const roomId = String(chatData.id);
      
      // 테스트 파일과 동일한 방식으로 사용자 메시지 처리
      const requestBody = {
        message: message,
        user_id: currentUserTurn.speaker_id  // 백엔드에서 받은 speaker_id 사용
      };
      
      console.log('📤 Sending user message request:', requestBody);
      
      const response = await fetch(`${apiBaseUrl}/api/chat/debate/${roomId}/process-user-message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '사용자 메시지 처리 실패');
      }
      
      const result = await response.json();
      console.log('✅ User message processed:', result);
      
      if (result.status === 'success') {
        console.log('✅ User message successfully processed - clearing user turn state');
        
        // 사용자 차례 종료 (테스트 파일과 동일한 플로우)
        setWaitingForUserInput(false);
        setCurrentUserTurn(null);
        
        // 다음 AI 응답 자동 요청 (약간의 지연 후)
        console.log('🔄 Requesting next AI message...');
        setTimeout(() => {
          handleRequestNextMessage();
        }, 1000);
        
      } else if (result.status === 'error' && result.reason === 'not_your_turn') {
        console.error('❌ Not user turn:', result.message);
        alert(`It's currently ${result.next_speaker}'s turn.`);
        setWaitingForUserInput(false);
        setCurrentUserTurn(null);
      } else {
        throw new Error(result.message || 'Failed to process user message');
      }
      
    } catch (error) {
      console.error('❌ Error processing user message:', error);
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      alert(`Error occurred while processing message: ${errorMessage}`);
      setWaitingForUserInput(false);
      setCurrentUserTurn(null);
    }
  };

  // 디버깅용 헬퍼 함수들
  const debugHelpers = {
    getCurrentState: () => ({
      waitingForUserInput,
      currentUserTurn,
      username,
      chatData: chatData ? { id: chatData.id, title: chatData.title } : null,
      isGeneratingResponse
    }),
    forceUserTurn: (speaker_id: string, role: string) => {
      console.log('🔧 Forcing user turn:', { speaker_id, role });
      setCurrentUserTurn({ speaker_id, role });
      setWaitingForUserInput(true);
      setIsGeneratingResponse(false);
    },
    clearUserTurn: () => {
      console.log('🔧 Clearing user turn');
      setWaitingForUserInput(false);
      setCurrentUserTurn(null);
    }
  };

  // 브라우저 콘솔에서 디버깅할 수 있도록 window 객체에 노출
  useEffect(() => {
    (window as any).debugChat = debugHelpers;
    console.log('🔧 Debug helpers available: window.debugChat');
  }, [waitingForUserInput, currentUserTurn, username, chatData, isGeneratingResponse]);

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 w-screen h-screen bg-white flex justify-center items-center">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-8 w-48 bg-gray-200 rounded mb-4"></div>
          <div className="h-4 w-32 bg-gray-200 rounded"></div>
          <div className="text-sm text-blue-600 mt-4">V2 Loading...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-50 w-screen h-screen bg-white flex justify-center items-center flex-col">
        <p className="text-xl text-gray-500 mb-4">{error}</p>
        <div className="text-sm text-red-600 mb-4">V2 Error Page</div>
        <button 
          onClick={handleBackToOpenChat}
          className="px-4 py-2 bg-black text-white rounded-md"
        >
          Back to Open Chat
        </button>
      </div>
    );
  }

  if (!chatData) {
    return (
      <div className="fixed inset-0 z-50 w-screen h-screen bg-white flex justify-center items-center">
        <p className="text-xl text-gray-500">Chat not found (V2)</p>
      </div>
    );
  }

  // V2 구조에서는 debate 타입만 지원 (점진적 확장 예정)
  if (chatData.dialogueType !== 'debate') {
    return (
      <div className="fixed inset-0 z-50 w-screen h-screen bg-white flex justify-center items-center flex-col">
        <p className="text-xl text-gray-500 mb-4">
          V2 구조는 현재 토론(debate) 채팅만 지원합니다.
        </p>
        <div className="text-sm text-blue-600 mb-4">
          현재 채팅 타입: {chatData.dialogueType}
        </div>
        <button 
          onClick={() => router.push(`/chat?id=${chatData.id}`)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md mr-2"
        >
          기존 버전으로 보기
        </button>
        <button 
          onClick={handleBackToOpenChat}
          className="px-4 py-2 bg-gray-600 text-white rounded-md"
        >
          Back to Open Chat
        </button>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 w-screen h-screen bg-white">
      {/* 메인 채팅 컨테이너 */}
      <div className="h-full">
        <DebateChatContainer
          room={{
            ...chatData,
            id: String(chatData.id),
            dialogueType: chatData.dialogueType || 'debate'
          }}
          messages={chatData.messages || []}
          npcDetails={chatData.npcDetails || []}
          onSendMessage={handleSendMessage}
          onRefresh={handleRefreshChat}
          isLoading={loading}
          isGeneratingResponse={isGeneratingResponse}
          username={username || 'You'}
          onEndChat={() => router.push('/open-chat')}
          userRole={
            chatData.pro?.includes(username) || chatData.pro?.includes('You') ? 'pro' :
            chatData.con?.includes(username) || chatData.con?.includes('You') ? 'con' :
            'neutral'
          }
          onRequestNextMessage={handleRequestNextMessage}
          typingMessageIds={typingMessageIds}
          onTypingComplete={handleTypingComplete}
          waitingForUserInput={waitingForUserInput}
          currentUserTurn={currentUserTurn}
          onProcessUserMessage={handleProcessUserMessage}
        />
      </div>
      
      {/* 글로벌 스타일 */}
      <style jsx global>{`
        body.chat-page-open header {
          display: none !important;
        }
        body.chat-page-open {
          overflow: hidden;
        }
      `}</style>
    </div>
  );
} 