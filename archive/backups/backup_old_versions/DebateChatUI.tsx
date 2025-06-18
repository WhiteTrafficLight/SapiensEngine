'use client';

import React, { useState, useRef, useEffect } from 'react';
import { UserIcon, PaperAirplaneIcon, ArrowPathIcon, ArrowDownCircleIcon } from '@heroicons/react/24/outline';
import { ChatMessage, ChatRoom, NpcDetail } from '@/lib/ai/chatService';
import { formatTimestamp } from '@/lib/utils/dateUtils';
import { useRouter } from 'next/router';
import TypingMessage from './TypingMessage';

interface DebateChatUIProps {
  room: ChatRoom;
  messages: ChatMessage[];
  npcDetails: NpcDetail[];
  onSendMessage: (message: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
  isGeneratingResponse: boolean;
  username?: string;
  onEndChat?: () => void;
  userRole?: string;
  onRequestNextMessage?: () => void;
}

const DebateChatUI: React.FC<DebateChatUIProps> = ({
  room,
  messages,
  npcDetails: initialNpcDetails,
  onSendMessage,
  onRefresh,
  isLoading,
  isGeneratingResponse,
  username = 'You',
  onEndChat,
  userRole,
  onRequestNextMessage
}) => {
  // 모더레이터 스타일 정보 매핑
  const moderatorStyles = [
    { id: '0', name: 'Jamie the Host' },
    { id: '1', name: 'Dr. Lee' },
    { id: '2', name: 'Zuri Show' },
    { id: '3', name: 'Elias of the End' },
    { id: '4', name: 'Miss Hana' }
  ];
  
  const [messageText, setMessageText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageContainerRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);
  const [userProfilePicture, setUserProfilePicture] = useState<string | null>(null);
  const [npcDetails, setNpcDetails] = useState<Record<string, NpcDetail>>({});
  const [selectedNpcId, setSelectedNpcId] = useState<string | null>(null);
  const [isUserTurn, setIsUserTurn] = useState<boolean>(false);
  const [turnIndicatorVisible, setTurnIndicatorVisible] = useState<boolean>(false);
  const [inputDisabled, setInputDisabled] = useState<boolean>(true);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const userSide = userRole || 'neutral';
  
  // Next 메시지 생성 상태
  const [isGeneratingNext, setIsGeneratingNext] = useState<boolean>(false);
  
  // 타이핑 애니메이션을 위한 상태
  const [lastMessageCount, setLastMessageCount] = useState<number>(0);
  const [typingMessageIds, setTypingMessageIds] = useState<Set<string>>(new Set());
  
  // Check if device is mobile
  useEffect(() => {
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    
    return () => {
      window.removeEventListener('resize', checkIfMobile);
    };
  }, []);
  
  // Load NPC details
  useEffect(() => {
    const loadNpcDetails = async () => {
      const details: Record<string, NpcDetail> = {};
      
      // 기존 npcDetails 프롭스의 NPC를 Record 형태로 변환
      if (initialNpcDetails && initialNpcDetails.length > 0) {
        initialNpcDetails.forEach(npc => {
          details[npc.id] = npc;
        });
        setNpcDetails(details);
        return;
      }
      
      // 기존 프롭스에 NPC 정보가 없는 경우 API에서 가져오기
      const npcIds = [...(room.pro || []), ...(room.con || []), ...(room.neutral || [])].filter(id => 
        !room.participants.users.includes(id)
      );
      
      for (const npcId of npcIds) {
        try {
          const response = await fetch(`/api/npc/get?id=${encodeURIComponent(npcId)}`);
          if (response.ok) {
            const npcDetail = await response.json();
            details[npcId] = npcDetail;
          }
        } catch (error) {
          console.error(`Error loading NPC details for ${npcId}:`, error);
        }
      }
      
      setNpcDetails(details);
    };
    
    loadNpcDetails();
  }, [initialNpcDetails, room.pro, room.con, room.neutral, room.participants.users]);
  
  // Fetch user profile to get profile picture
  useEffect(() => {
    if (username) {
      fetchUserProfile(username);
    }
  }, [username]);
  
  // Fetch user profile to get profile picture
  const fetchUserProfile = async (username: string) => {
    try {
      console.log('Fetching user profile for:', username);
      const response = await fetch('/api/user/profile');
      if (response.ok) {
        const profileData = await response.json();
        console.log('Profile data received:', profileData);
        if (profileData && profileData.profileImage) {
          console.log('Setting profile image:', profileData.profileImage);
          setUserProfilePicture(profileData.profileImage);
        } else if (profileData && profileData.profilePicture) {
          console.log('Setting profile picture:', profileData.profilePicture);
          setUserProfilePicture(profileData.profilePicture);
        } else {
          console.log('No profile image found in profileData:', profileData);
        }
      } else {
        console.error('Error response from profile API:', response.status);
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
    }
  };
  
  // Auto-scroll to the bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // Function to check if input should be disabled
  const isInputDisabled = (): boolean => {
    return !isUserTurn || isGeneratingResponse;
  };
  
  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Only allow submission when it's the user's turn and there's text
    if (messageText.trim() && isUserTurn) {
      console.log('💬 User is submitting message:', messageText);
      
      // Disable input field immediately to prevent double submissions
      setInputDisabled(true);
      
      // Send the message - make sure to pass the entire message at once
      onSendMessage(messageText);
      
      // Clear the input field after sending
      setMessageText('');
      
      // Turn off user turn indicators
      setIsUserTurn(false);
      setTurnIndicatorVisible(false);
      
      // Wait a bit before enabling the input field again (if it's still the user's turn)
      setTimeout(() => {
        if (inputRef.current && isUserTurn) {
          setInputDisabled(false);
          inputRef.current.focus();
        }
      }, 1000);
    }
  };

  // Input field render - add prominent visual cue when it's user's turn
  const renderInputField = () => {
    return (
      <textarea
        ref={inputRef}
        value={messageText}
        onChange={(e) => setMessageText(e.target.value)}
        onKeyDown={handleKeyPress}
        placeholder={isUserTurn ? "지금은 당신의 차례입니다. 메시지를 입력하세요." : "다음 버튼을 눌러 대화를 계속하세요."}
        className={`w-full resize-none outline-none p-2 ${
          isUserTurn 
            ? "bg-white border-2 border-blue-500 animate-pulse focus:animate-none" 
            : "bg-gray-100 text-gray-500"
        }`}
        style={{
          minHeight: '60px',
          borderRadius: '12px',
          transition: 'all 0.3s ease',
          boxShadow: isUserTurn ? '0 0 8px rgba(59, 130, 246, 0.5)' : 'none'
        }}
        disabled={isInputDisabled()}
      />
    );
  };
  
  // Apply a global CSS animation for the user turn indicator
  useEffect(() => {
    // Add the animation style to the document head when it's user's turn
    if (isUserTurn && turnIndicatorVisible) {
      const styleId = 'user-turn-animation-style';
      
      // Only add if not already present
      if (!document.getElementById(styleId)) {
        const style = document.createElement('style');
        style.id = styleId;
        style.innerHTML = `
          @keyframes userTurnPulse {
            0% { box-shadow: 0 0 5px rgba(59, 130, 246, 0.5); }
            50% { box-shadow: 0 0 15px rgba(59, 130, 246, 0.8); }
            100% { box-shadow: 0 0 5px rgba(59, 130, 246, 0.5); }
          }
          
          .user-turn-active {
            animation: userTurnPulse 2s infinite;
            border: 2px solid #3b82f6 !important;
          }
          
          @keyframes micBounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
          }
          
          .mic-bounce {
            animation: micBounce 1s infinite;
            color: #3b82f6;
          }
        `;
        document.head.appendChild(style);
      }
      
      // Focus the input field when it's the user's turn
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
    
    // Clean up styles on unmount
    return () => {
      const styleElement = document.getElementById('user-turn-animation-style');
      if (styleElement) {
        styleElement.remove();
      }
    };
  }, [isUserTurn, turnIndicatorVisible]);

  // Listen for next-speaker-update events from socketClient
  useEffect(() => {
    const handleNextSpeakerUpdate = (event: CustomEvent) => {
      if (event.detail && event.detail.is_user === true) {
        console.log('🎤 User turn detected from event!', event.detail);
        setIsUserTurn(true);
        setTurnIndicatorVisible(true);
        
        // Focus the input field
        setTimeout(() => {
          if (inputRef.current) {
            inputRef.current.focus();
          }
        }, 100);
      } else {
        console.log('🎤 Non-user turn detected from event', event.detail);
        setIsUserTurn(false);
        setTurnIndicatorVisible(false);
      }
    };
    
    // Add the event listener
    document.addEventListener('next-speaker-update', handleNextSpeakerUpdate as EventListener);
    
    // Clean up on unmount
    return () => {
      document.removeEventListener('next-speaker-update', handleNextSpeakerUpdate as EventListener);
    };
  }, []);
  
  // Handle key press (Enter to send)
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isInputDisabled()) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };
  
  // Next 메시지 요청 함수
  const handleNextMessage = async () => {
    if (isGeneratingNext) return;
    
    setIsGeneratingNext(true);
    console.log(`🎯 Next 버튼 클릭 - 방 ${room.id}에 대한 다음 메시지 요청`);
    
    try {
      const response = await fetch(`http://localhost:8000/api/chat/debate/${room.id}/next-message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Next 메시지 요청 실패:', errorData);
        throw new Error(errorData.detail || 'Next 메시지 요청 실패');
      }
      
      const data = await response.json();
      console.log('✅ Next 메시지 요청 성공:', data);
      
      if (data.status === 'completed') {
        console.log('🏁 토론 완료');
      }
      
    } catch (error) {
      console.error('❌ Next 메시지 요청 중 오류:', error);
    } finally {
      setIsGeneratingNext(false);
    }
  };
  
  // Check if this is a debate room
  const isDebateRoom = room.dialogueType === 'debate';
  
  // Helper function to determine if the next message button should be shown
  const shouldShowNextMessageButton = () => {
    if (!isDebateRoom || !onRequestNextMessage || isGeneratingResponse) return false;
    
    // Show the button if there are messages and we're not generating a response
    return messages.length > 0;
  };
  
  // Get name from ID with proper handling for moderator
  const getNameFromId = (id: string, isUser: boolean): string => {
    // 모더레이터 처리
    if (id === 'Moderator' || id === 'moderator') {
      return moderatorInfo.name;
    }
    
    if (isUser) {
      return username;
    }
    
    // Check if it's a known NPC
    const npc = npcDetails[id];
    if (npc) {
      return npc.name;
    }
    
    // If no NPC found, try to format the ID
    return id.charAt(0).toUpperCase() + id.slice(1);
  };
  
  const getDefaultAvatar = (name: string) => {
    // For moderator, use the correct moderator image
    if (name === moderatorInfo.name || name === 'Moderator') {
      return moderatorInfo.profileImage;
    }
    return `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(name)}`;
  };
  
  // Get NPC profile image
  const getNpcProfileImage = (npcId: string): string => {
    // 모더레이터 처리
    if (npcId === 'Moderator' || npcId === 'moderator') {
      return moderatorInfo.profileImage;
    }
    
    const npc = npcDetails[npcId];
    if (npc && npc.portrait_url) {
      return npc.portrait_url;
    }
    // Fallback to default portrait location
    return `/portraits/${npcId}.png`;
  };
  
  // Get profile image for any participant
  const getProfileImage = (id: string, isUser: boolean): string => {
    // 모더레이터 처리
    if (id === 'Moderator' || id === 'moderator') {
      return moderatorInfo.profileImage;
    }
    
    if (isUser) {
      if (userProfilePicture && userProfilePicture.length > 0) {
        return userProfilePicture;
      }
      return getDefaultAvatar(username);
    }
    return getNpcProfileImage(id);
  };
  
  // Check if ID is a user participant
  const isUserParticipant = (id: string): boolean => {
    return room.participants.users.includes(id) || id === username;
  };
  
  // Check if an ID belongs to pro, con, or neutral based on room data
  const getParticipantSide = (id: string, isUser: boolean): 'pro' | 'con' | 'neutral' | 'moderator' => {
    // 메시지에서 해당 발신자의 메시지 객체 찾기
    const msg = messages.find(m => m.sender === id);
    
    // 모더레이터 메시지 확인 (sender, isSystemMessage, role 등으로 확인)
    if (id === 'Moderator' || msg?.isSystemMessage || msg?.role === 'moderator') {
      return 'moderator';
    }
    
    // 기존 로직과 동일
    if (proParticipants.includes(id)) {
      return 'pro';
    }
    
    if (conParticipants.includes(id)) {
      return 'con';
    }
    
    return 'neutral';
  };
  
  // Separate participants by side (make them unique)
  const proParticipants = [...new Set(room.pro || [])];
  const conParticipants = [...new Set(room.con || [])];
  const neutralParticipants = [...new Set(room.neutral || [])];
  
  // Get all unique senders from messages for visibility
  const uniqueSenders = Array.from(new Set(messages.map(msg => msg.sender)));
  
  // Ensure all message senders appear in the UI even if not in pro/con/neutral lists
  uniqueSenders.forEach(sender => {
    // 모더레이터는 참가자 리스트에 추가하지 않음
    if (sender === 'Moderator' || sender === 'moderator') {
      return;
    }
    
    const isInAnyList = 
      proParticipants.includes(sender) || 
      conParticipants.includes(sender) || 
      neutralParticipants.includes(sender);
    
    if (!isInAnyList) {
      // Find message to check if user
      const msg = messages.find(m => m.sender === sender);
      const isSenderUser = msg?.isUser || sender === username;
      
      // 메시지의 role이 moderator인 경우도 제외
      if (msg?.role === 'moderator' || msg?.isSystemMessage) {
        return;
      }
      
      // Only add to a position list if not already in any list
      if (isSenderUser) {
        // Don't add user if already exists in participants.users
        const isAlreadyInUsers = room.participants.users.some(userId => 
          userId === sender || userId === username
        );
        
        if (!isAlreadyInUsers) {
          neutralParticipants.push(sender);
        }
      } else {
        // NPC가 이미 pro나 con에 있는지 다시 한번 확인
        const isInProOrCon = 
          (room.pro && room.pro.includes(sender)) || 
          (room.con && room.con.includes(sender));
        
        if (!isInProOrCon) {
        // Add NPC to neutral as fallback (only if not already included)
        neutralParticipants.push(sender);
        }
      }
    }
  });
  
  // 모더레이터 Participants 추가 (숨김)
  const moderatorParticipants = ['Moderator'];
  
  // Initialize socket client for npc-selected events
  useEffect(() => {
    // Only initialize if we have a valid room
    if (!room || !room.id) return;
    
    const initSocket = async () => {
      try {
        // Import socketClient dynamically to avoid SSR issues
        const { default: socketClient } = await import('@/lib/socket/socketClient');
        
        // Initialize with current username or default
        const storedUsername = sessionStorage.getItem('chat_username') || username;
        await socketClient.init(storedUsername);
        
        // Join the room - use roomId directly as string (String conversion removed)
        const roomId = String(room.id); // 문자열로 정규화
        console.log(`DebateChatUI: Joining room ${roomId} (${typeof roomId})`);
        socketClient.joinRoom(roomId, storedUsername);
        
        // Add event handler for npc-selected
        socketClient.on('npc-selected', (data: { npc_id: string }) => {
          console.log('NPC selected for response:', data.npc_id);
          setSelectedNpcId(data.npc_id);
          
          // Auto-clear after 3 seconds
          setTimeout(() => {
            setSelectedNpcId(null);
          }, 3000);
        });
        
        // Cleanup on unmount
        return () => {
          socketClient.leaveRoom(roomId, storedUsername); // 동일한 roomId 사용
          socketClient.off('npc-selected', () => {});
        };
      } catch (error) {
        console.error('Error initializing socket for debate UI:', error);
      }
    };
    
    initSocket();
  }, [room.id, username]);
  
  // Add styling for selected NPC
  const getProfileStyle = (id: string, side: 'pro' | 'con' | 'neutral' | 'moderator') => {
    // Base styles
    const baseStyle = {
      ...profileImageContainerStyle, 
      border: getBorderStyle(side),
      transition: 'all 0.3s ease'
    };
    
    // Add highlighted style if this NPC is currently selected
    if (selectedNpcId === id) {
      return {
        ...baseStyle,
        boxShadow: '0 0 10px 3px rgba(59, 130, 246, 0.6)',
        transform: 'scale(1.1)'
      };
    }
    
    return baseStyle;
  };
  
  // Styled components (inline styles)
  const mainContainerStyle = {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    width: '100%',
    maxWidth: '100%',
    backgroundColor: '#f9fafb'
  };
  
  const headerStyle = {
    backgroundColor: 'white',
    borderBottom: '1px solid #e5e7eb',
    padding: '16px',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };
  
  const titleStyle = {
    fontSize: '1.25rem',
    fontWeight: 'bold',
    color: '#111827',
    marginRight: '8px'
  };
  
  const bannerStyle = {
    backgroundImage: 'linear-gradient(to right, #dbeafe, white, #fee2e2)',
    padding: '8px 16px',
    textAlign: 'center' as const,
    borderBottom: '1px solid #e5e7eb'
  };
  
  const chatAreaStyle = {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '16px'
  };
  
  const participantsContainerStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px'
  };
  
  const profileContainerStyle = {
    marginBottom: '16px',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center'
  };
  
  const profileImageContainerStyle = {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    overflow: 'hidden',
    marginBottom: '8px'
  };
  
  const profileImageStyle = {
    width: '100%',
    height: '100%',
    objectFit: 'cover' as const,
    objectPosition: 'center top' as const
  };
  
  const nameStyle = {
    fontSize: '0.875rem',
    fontWeight: '500',
    textAlign: 'center' as const,
    maxWidth: '80px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const
  };
  
  const roleStyle = {
    fontSize: '0.75rem',
    textAlign: 'center' as const
  };
  
  const messagesContainerStyle = {
    marginTop: '32px',
    paddingBottom: '64px'
  };
  
  const inputContainerStyle = {
    backgroundColor: 'white',
    borderTop: '1px solid #e5e7eb',
    padding: '16px'
  };
  
  // Border colors for profile images based on side
  const getBorderStyle = (side: 'pro' | 'con' | 'neutral' | 'moderator') => {
    if (side === 'pro') return '2px solid #3b82f6';
    if (side === 'con') return '2px solid #ef4444';
    if (side === 'moderator') return '2px solid #f59e0b'; // 진행자는 주황색
    return '2px solid #9ca3af';
  };
  
  // Text colors for roles based on side
  const getTextColor = (side: 'pro' | 'con' | 'neutral' | 'moderator') => {
    if (side === 'pro') return '#1d4ed8';
    if (side === 'con') return '#b91c1c';
    if (side === 'moderator') return '#b45309'; // 진행자는 주황색
    return '#4b5563';
  };
  
  useEffect(() => {
    // 초기 메시지 디버깅
    if (messages && messages.length > 0) {
      console.log(`DebateChatUI: Received ${messages.length} initial messages`);
      console.log(`First message from: ${messages[0].sender}, isUser: ${messages[0].isUser}`);
      console.log(`isSystemMessage: ${messages[0].isSystemMessage}, role: ${messages[0].role}`);
      console.log(`Message text: ${messages[0].text.substring(0, 100)}...`);
      console.log(`Full first message:`, messages[0]);
      console.log(`Message contains 초기메시지에용: ${messages[0].text.includes('초기메시지에용')}`);
      
      // Moderator 메시지가 있는지 확인
      const moderatorMsg = messages.find(msg => 
        msg.sender === 'Moderator' || 
        msg.isSystemMessage === true || 
        msg.role === 'moderator'
      );
      
      if (moderatorMsg) {
        console.log(`✅ Moderator message found: ${moderatorMsg.text.substring(0, 100)}...`);
        console.log(`Moderator message details:`, {
          sender: moderatorMsg.sender,
          isSystemMessage: moderatorMsg.isSystemMessage,
          role: moderatorMsg.role,
          text: moderatorMsg.text
        });
      } else {
        console.log(`❌ No moderator message found in messages array`);
      }
    } else {
      console.log(`DebateChatUI: No initial messages`);
    }
  }, [messages]);
  
  // 메시지 답장 핸들러 함수
  const handleReplyToMessage = (message: ChatMessage) => {
    // 현재 구현에서는 실제로 답장 기능은 없으므로 로그만 남김
    console.log("Reply to message:", message);
  };
  
  // 모더레이터 정보 가져오기
  const getModeratorInfo = () => {
    console.log('🎭 [DebateChatUI] getModeratorInfo called');
    console.log('🎭 [DebateChatUI] room object:', room);
    console.log('🎭 [DebateChatUI] room.moderator:', (room as any).moderator);
    
    const moderatorConfig = (room as any).moderator;
    if (moderatorConfig && moderatorConfig.style_id) {
      console.log('🎭 [DebateChatUI] Found moderator config:', moderatorConfig);
      const style = moderatorStyles.find(s => s.id === moderatorConfig.style_id);
      console.log('🎭 [DebateChatUI] Found style:', style);
      return {
        name: style?.name || 'Jamie the Host',
        profileImage: `/portraits/Moderator${moderatorConfig.style_id}.png`
      };
    }
    console.log('🎭 [DebateChatUI] No moderator config found, using default');
    return {
      name: 'Jamie the Host',
      profileImage: '/portraits/Moderator0.png'
    };
  };
  
  const moderatorInfo = getModeratorInfo();
  
  // 메시지 렌더링 함수
  const renderMessage = (message: ChatMessage, index: number) => {
    const isUser = isUserParticipant(message.sender);
    const senderName = getNameFromId(message.sender, isUser);
    const avatar = getProfileImage(message.sender, isUser);
    const isCurrentUserTurn = isUserTurn && isUser;
    
    // 임시 대기 메시지인지 확인
    const isTempWaitingMessage = message.id.startsWith('temp-waiting-');
    
    return (
      <div key={message.id} style={{ 
        marginBottom: '20px',
        opacity: isCurrentUserTurn ? 1 : 0.95,
        transform: isCurrentUserTurn ? 'scale(1.02)' : 'scale(1)',
        transition: 'all 0.3s ease'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          animation: `fadeIn 0.5s ease-in-out ${index * 0.1}s both`
        }}>
          {/* Profile Image */}
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            overflow: 'hidden',
            border: '2px solid #e5e7eb',
            flexShrink: 0
          }}>
            <img
              src={avatar}
              alt={senderName}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover'
              }}
            />
          </div>
          
          {/* Message Content */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Sender Name */}
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: message.role === 'moderator' ? '#7c3aed' : '#374151',
              marginBottom: '4px'
            }}>
              {senderName}
              {message.role === 'moderator' && (
                <span style={{
                  background: 'linear-gradient(135deg, #7c3aed, #a855f7)',
                  color: 'white',
                  fontSize: '10px',
                  padding: '2px 6px',
                  borderRadius: '8px',
                  marginLeft: '8px',
                  fontWeight: '500'
                }}>
                  MODERATOR
                </span>
              )}
            </div>
            
            {/* Message Text */}
            <div style={{
              background: message.role === 'moderator' ? 
                'linear-gradient(135deg, #f3e8ff, #ede9fe)' : 
                (isUser ? '#e0f2fe' : '#f8fafc'),
              padding: '12px 16px',
              borderRadius: '12px',
              border: message.role === 'moderator' ? '1px solid #c4b5fd' : '1px solid #e5e7eb',
              position: 'relative',
              ...(isTempWaitingMessage && {
                background: 'linear-gradient(135deg, #fef3c7, #fde68a)',
                border: '1px solid #f59e0b',
                animation: 'pulse 2s infinite'
              })
            }}>
              {isTempWaitingMessage ? (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: '#92400e',
                  fontStyle: 'italic'
                }}>
                  <div style={{
                    display: 'flex',
                    gap: '4px'
                  }}>
                    <div style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#f59e0b',
                      animation: 'bounce 1.4s infinite ease-in-out'
                    }} />
                    <div style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#f59e0b',
                      animation: 'bounce 1.4s infinite ease-in-out 0.16s'
                    }} />
                    <div style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      backgroundColor: '#f59e0b',
                      animation: 'bounce 1.4s infinite ease-in-out 0.32s'
                    }} />
                  </div>
                  {message.text}
                </div>
              ) : (
                <div style={{
                  color: '#374151',
                  lineHeight: '1.6',
                  fontSize: '15px',
                  whiteSpace: 'pre-wrap'
                }}>
                  {typingMessageIds.has(message.id) ? (
                    <TypingMessage
                      text={message.text}
                      speed={30}
                      delay={200}
                      enabled={true}
                      showCursor={true}
                      autoStart={true}
                      onTypingComplete={() => handleTypingComplete(message.id)}
                      style={{
                        color: '#374151',
                        lineHeight: '1.6',
                        fontSize: '15px',
                        whiteSpace: 'pre-wrap'
                      }}
                    />
                  ) : (
                    message.text
                  )}
                </div>
              )}
              
              {/* 인용 정보 표시 */}
              {message.citations && message.citations.length > 0 && (
                <div style={{
                  marginTop: '12px',
                  padding: '8px',
                  background: 'rgba(59, 130, 246, 0.1)',
                  borderRadius: '6px',
                  fontSize: '12px'
                }}>
                  <strong>출처:</strong>
                  <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                    {message.citations.map((citation, idx) => (
                      <li key={idx} style={{ marginBottom: '2px' }}>
                        [{citation.id}] {citation.source}
                        {citation.location && ` (${citation.location})`}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            {/* Timestamp */}
            <div style={{
              fontSize: '12px',
              color: '#9ca3af',
              marginTop: '4px'
            }}>
              {new Date(message.timestamp).toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </div>
          </div>
        </div>
      </div>
    );
  };
  
  // 새로운 메시지가 추가되었는지 감지
  useEffect(() => {
    if (messages.length > lastMessageCount) {
      const newMessages = messages.slice(lastMessageCount);
      const newTypingIds = new Set(typingMessageIds);
      
      // 새로운 메시지들 중 사용자가 아닌 메시지에 타이핑 애니메이션 적용
      newMessages.forEach(message => {
        // 사용자 메시지인지 확인 (username과 비교)
        const isUser = room.participants.users.includes(message.sender) || message.sender === username;
        if (!isUser && !message.id.startsWith('temp-waiting-')) {
          newTypingIds.add(message.id);
        }
      });
      
      setTypingMessageIds(newTypingIds);
      setLastMessageCount(messages.length);
    }
  }, [messages.length, lastMessageCount, typingMessageIds, room.participants.users, username]);
  
  // 타이핑 완료 핸들러
  const handleTypingComplete = (messageId: string) => {
    setTypingMessageIds(prev => {
      const newSet = new Set(prev);
      newSet.delete(messageId);
      return newSet;
    });
  };
  
  return (
    <div style={mainContainerStyle}>
      {/* CSS 애니메이션 정의 */}
      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes bounce {
          0%, 80%, 100% {
            transform: scale(0);
          }
          40% {
            transform: scale(1);
          }
      }
      
      @keyframes pulse {
          0% {
            box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
          }
          70% {
            box-shadow: 0 0 0 10px rgba(245, 158, 11, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
          }
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      
      {/* Header */}
      <div style={headerStyle}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <h2 style={titleStyle}>{room.title}</h2>
          <button 
            onClick={onRefresh} 
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '4px',
              borderRadius: '4px',
              border: 'none',
              backgroundColor: 'transparent',
              cursor: 'pointer'
            }}
            disabled={isLoading}
          >
            <ArrowPathIcon style={{ 
              height: '16px', 
              width: '16px', 
              color: '#6b7280',
              animation: isLoading ? 'spin 1s linear infinite' : 'none'
            }} />
          </button>
        </div>
        
        {onEndChat && (
          <button 
            onClick={onEndChat}
            style={{
              padding: '4px 12px',
              fontSize: '0.75rem',
              backgroundColor: '#ef4444',
              color: 'white',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            End Conversation
          </button>
        )}
      </div>
      
      {/* Topic Banner */}
      <div style={bannerStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ width: '33%', textAlign: 'left', color: '#1d4ed8', fontWeight: 500 }}>Pro</div>
          <div style={{ width: '33%', color: '#4b5563', fontWeight: 500 }}>Neutral</div>
          <div style={{ width: '33%', textAlign: 'right', color: '#dc2626', fontWeight: 500 }}>Con</div>
        </div>
      </div>
      
      {/* Main chat area */}
      <div 
        style={chatAreaStyle}
        ref={messageContainerRef}
      >
        <div style={participantsContainerStyle}>
          {/* Pro Side (Left) */}
          <div style={{ borderRight: '1px solid #e5e7eb', paddingRight: '16px' }}>
            {proParticipants.map(id => {
              const isUser = isUserParticipant(id);
              const name = getNameFromId(id, isUser);
              const avatar = getProfileImage(id, isUser);
              
              return (
                <div key={`pro-${id}`} style={profileContainerStyle}>
                  <div style={{ 
                    ...getProfileStyle(id, 'pro'),
                    // 사용자의 차례이고 사용자가 이 참가자인 경우 하이라이트
                    ...(isUserTurn && isUser ? {
                      boxShadow: '0 0 20px 8px rgba(34, 197, 94, 0.9)',
                      transform: 'scale(1.2)',
                      border: '3px solid #22c55e'
                    } : {})
                  }}>
                    <img 
                      src={avatar} 
                      alt={name}
                      style={profileImageStyle}
                    />
                  </div>
                  <div style={nameStyle}>{name}</div>
                  <div style={roleStyle}>PRO</div>
                </div>
              );
            })}
          </div>
          
          {/* Neutral (Center) */}
          <div style={{ borderRight: '1px solid #e5e7eb', padding: '0 8px' }}>
            {neutralParticipants.map(id => {
              const isUser = isUserParticipant(id);
              const name = getNameFromId(id, isUser);
              const avatar = getProfileImage(id, isUser);
              
              return (
                <div key={`neutral-${id}`} style={profileContainerStyle}>
                  <div style={{ 
                    ...getProfileStyle(id, 'neutral'),
                    // 사용자의 차례이고 사용자가 이 참가자인 경우 하이라이트
                    ...(isUserTurn && isUser ? {
                      boxShadow: '0 0 20px 8px rgba(59, 130, 246, 0.9)',
                      transform: 'scale(1.2)',
                      border: '3px solid #3b82f6'
                    } : {})
                  }}>
                    <img 
                      src={avatar} 
                      alt={name}
                      style={profileImageStyle}
                    />
                  </div>
                  <div style={nameStyle}>{name}</div>
                  <div style={roleStyle}>NEUTRAL</div>
                </div>
              );
            })}
            
            {/* 모든 중립 참가자 다음에 모더레이터 프로필 추가 */}
            <div key="moderator" style={profileContainerStyle}>
              <div style={{ 
                ...getProfileStyle('moderator', 'neutral'),
                background: 'linear-gradient(135deg, #7c3aed, #a855f7)',
                border: '3px solid #8b5cf6'
              }}>
                <img
                  src={moderatorInfo.profileImage}
                  alt={moderatorInfo.name}
                  style={profileImageStyle}
                />
              </div>
              <div style={nameStyle}>{moderatorInfo.name}</div>
              <div style={{ ...roleStyle, color: '#7c3aed', fontWeight: 'bold' }}>MODERATOR</div>
            </div>
          </div>
          
          {/* Con Side (Right) */}
          <div style={{ paddingLeft: '16px' }}>
            {conParticipants.map(id => {
              const isUser = isUserParticipant(id);
              const name = getNameFromId(id, isUser);
              const avatar = getProfileImage(id, isUser);
              
              return (
                <div key={`con-${id}`} style={profileContainerStyle}>
                  <div style={{ 
                    ...getProfileStyle(id, 'con'),
                    // 사용자의 차례이고 사용자가 이 참가자인 경우 하이라이트
                    ...(isUserTurn && isUser ? {
                      boxShadow: '0 0 20px 8px rgba(239, 68, 68, 0.9)',
                      transform: 'scale(1.2)',
                      border: '3px solid #ef4444'
                    } : {})
                  }}>
                    <img 
                      src={avatar} 
                      alt={name}
                      style={profileImageStyle}
                    />
                  </div>
                  <div style={nameStyle}>{name}</div>
                  <div style={roleStyle}>CON</div>
                </div>
              );
            })}
          </div>
        </div>
        
        {/* Messages */}
        <div style={messagesContainerStyle}>
          <div ref={messageContainerRef} style={{
            flex: 1,
            overflowY: 'auto',
            padding: '20px',
            background: '#ffffff'
          }}>
            {room.messages && room.messages.length > 0 ? (
              room.messages.map((message, index) => renderMessage(message, index))
            ) : (
                <div style={{ 
                textAlign: 'center',
                color: '#9ca3af',
                fontSize: '16px',
                marginTop: '40px'
              }}>
                토론이 곧 시작됩니다...
                      </div>
                    )}
            <div ref={messagesEndRef} />
                  </div>
        </div>
      </div>
      
      {/* Input area */}
      <div style={{
        ...inputContainerStyle,
        ...(isUserTurn ? {
          boxShadow: '0 -10px 15px -3px rgba(59, 130, 246, 0.1)',
          padding: '16px',
          borderTop: '2px solid #3b82f6',
          backgroundColor: '#f0f9ff',
          transition: 'all 0.3s ease'
        } : {})
      }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px' }}>
          {renderInputField()}
          <button
            type="submit"
            disabled={!messageText.trim() || isInputDisabled()}
            style={{
              backgroundColor: !messageText.trim() || isInputDisabled() ? '#93c5fd' : '#2563eb',
              color: 'white',
              borderRadius: '9999px',
              width: '40px',
              height: '40px',
              border: 'none',
              cursor: !messageText.trim() || isInputDisabled() ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: !messageText.trim() || isInputDisabled() ? 0.7 : 1,
              transition: 'all 0.3s ease',
              transform: isUserTurn && messageText.trim() ? 'scale(1.1)' : 'scale(1)',
              boxShadow: isUserTurn && messageText.trim() ? '0 0 10px rgba(59, 130, 246, 0.7)' : 'none',
              animation: isUserTurn && messageText.trim() ? 'pulse 1.5s infinite' : 'none'
            }}
          >
            <PaperAirplaneIcon style={{ height: '20px', width: '20px' }} />
          </button>
          
          {/* Next 버튼 추가 */}
          <button
            type="button"
            onClick={handleNextMessage}
            disabled={isGeneratingNext}
            style={{
              backgroundColor: isGeneratingNext ? '#94a3b8' : '#10b981',
              color: 'white',
              borderRadius: '12px',
              padding: '8px 16px',
              border: 'none',
              cursor: isGeneratingNext ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              fontSize: '14px',
              fontWeight: '600',
              opacity: isGeneratingNext ? 0.7 : 1,
              transition: 'all 0.3s ease',
              minWidth: '80px'
            }}
          >
            {isGeneratingNext ? (
              <>
                <div style={{
                  width: '16px',
                  height: '16px',
                  border: '2px solid #ffffff',
                  borderTop: '2px solid transparent',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
                생성중...
              </>
            ) : (
              <>
                <ArrowDownCircleIcon style={{ height: '18px', width: '18px' }} />
                Next
              </>
            )}
          </button>
        </form>
        
        {/* Show a message indicating it's not user's turn */}
        {!isUserTurn && !isGeneratingResponse && (
          <div style={{
            textAlign: 'center',
            fontSize: '0.85rem',
            color: '#6b7280',
            marginTop: '8px'
          }}>
            현재 다른 참가자의 발언 차례입니다. 당신의 차례가 되면 알려드립니다.
        </div>
      )}
      </div>
    </div>
  );
};

export default DebateChatUI; 