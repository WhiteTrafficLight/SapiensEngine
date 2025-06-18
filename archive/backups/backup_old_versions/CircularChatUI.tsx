'use client';

import React, { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon, ArrowLeftIcon, StopIcon } from '@heroicons/react/24/outline';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import chatService, { ChatMessage as ChatMessageBase } from '@/lib/ai/chatService';
import socketClient from '@/lib/socket/socketClient';

// Extend the ChatMessage interface to include NPC information
interface ChatMessage extends ChatMessageBase {
  isNew?: boolean;
  senderName?: string;
  senderType?: string;
  portrait_url?: string;
  npc_id?: string;
}

// NPC details interface
interface NpcDetail {
  id: string;
  name: string;
  description?: string;
  portrait_url?: string;
  is_custom: boolean;
}

interface CircularChatUIProps {
  chatId: string;
  chatTitle: string;
  participants: {
    users: string[];
    npcs: string[];
  };
  initialMessages?: ChatMessage[];
  onBack?: () => void;
}

const CircularChatUI: React.FC<CircularChatUIProps> = ({
  chatId,
  chatTitle,
  participants,
  initialMessages = [],
  onBack
}) => {
  const router = useRouter();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isThinking, setIsThinking] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState('');
  const [npcDetails, setNpcDetails] = useState<Record<string, NpcDetail>>({});
  const [socketClientInstance, setSocketClientInstance] = useState<any>(null);
  const [isSocketConnected, setIsSocketConnected] = useState(false);
  const [timelinePosition, setTimelinePosition] = useState(1); // 1 = newest message, 0 = oldest
  const [activeMessageIndex, setActiveMessageIndex] = useState<number | null>(null);
  const [messageContainerRef, setMessageContainerRef] = useState<HTMLDivElement | null>(null);
  const [isScrolling, setIsScrolling] = useState(false);
  const [showPodcastModal, setShowPodcastModal] = useState(false);
  const [isGeneratingPodcast, setIsGeneratingPodcast] = useState(false);
  const [podcastProgress, setPodcastProgress] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const [circleRadius, setCircleRadius] = useState(0);
  const [windowDimensions, setWindowDimensions] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768
  });
  const [userProfilePicture, setUserProfilePicture] = useState<string | null>(null);
  const [isLoadingRoom, setIsLoadingRoom] = useState(true);
  
  // Get the current message to display based on timeline position
  const currentMessage = activeMessageIndex !== null 
    ? messages[activeMessageIndex] 
    : messages.length > 0 
      ? messages[messages.length - 1] 
      : null;
  
  // Load user information on component mount
  useEffect(() => {
    // Get username from session storage first
    const storedUsername = sessionStorage.getItem('chat_username');
    
    if (storedUsername) {
      setUsername(storedUsername);
      // Fetch user profile to get profile picture
      fetchUserProfile(storedUsername);
    } else {
      // Fetch current user or generate a username
      fetch('/api/user/current')
        .then(res => res.json())
        .then(data => {
          if (data && data.username) {
            setUsername(data.username);
            sessionStorage.setItem('chat_username', data.username);
            // Fetch profile picture
            fetchUserProfile(data.username);
          } else {
            const randomUsername = `User_${Math.floor(Math.random() * 10000)}`;
            setUsername(randomUsername);
            sessionStorage.setItem('chat_username', randomUsername);
          }
        })
        .catch(err => {
          console.error('Error fetching user:', err);
          const randomUsername = `User_${Math.floor(Math.random() * 10000)}`;
          setUsername(randomUsername);
          sessionStorage.setItem('chat_username', randomUsername);
        });
    }
  }, []);
  
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
  
  // Initialize socket connection
  useEffect(() => {
    if (!username) return;
    
    const initSocket = async () => {
      try {
        console.log('Starting socket initialization...');
        const instance = await socketClient.init(username);
        console.log('Socket client initialization completed');
        
        // 타입 단언을 사용하여 임시로 에러 해결
        const socketInstance = instance as any;
        
        // Ensure chatId is always a string for consistency
        const chatIdString = String(chatId);
        
        socketInstance.on('connect', () => {
          console.log('Socket connected - updating UI state');
          setIsSocketConnected(true);
          setError('');
          
          try {
            const joinResult = socketInstance.joinRoom?.(chatIdString);
            console.log('Room join result:', joinResult ? 'success' : 'failure');
          } catch (err) {
            console.warn('Failed to join room:', err);
          }
        });
        
        try {
          if (socketInstance.isConnected?.()) {
            setIsSocketConnected(true);
          }
        } catch (err) {
          console.warn('Failed to check connection status:', err);
        }
        
        setSocketClientInstance(socketInstance);
        
        // Join room with error handling
        console.log(`Attempting to join room: ${chatIdString}`);
        try {
          const joinResult = socketInstance.joinRoom?.(chatIdString);
          console.log('Room join result:', joinResult ? 'success' : 'failure');
        } catch (err) {
          console.warn('Failed to join room on init:', err);
        }
        
        // Set up event listeners
        socketInstance.on('new-message', (data: { roomId: string, message: ChatMessage }) => {
          console.log('New message received via socket:', data);
          const messageRoomId = String(data.roomId);
          const currentRoomId = String(chatId);
          
          if (messageRoomId === currentRoomId && data.message) {
            console.log(`✅ Message belongs to current room ${currentRoomId}, adding to UI`);
            setMessages(prev => [...prev, {...data.message, isNew: true}]);
            
            if (!data.message.isUser) {
              setIsThinking(false);
            }
            
            setTimelinePosition(1);
            setActiveMessageIndex(null);
          } else {
            console.log(`⚠️ Message for room ${messageRoomId} ignored (current room: ${currentRoomId})`);
          }
        });
        
        socketInstance.on('thinking', () => {
          setIsThinking(true);
        });
        
        socketInstance.on('npc-selected', (data: { npc_id: string }) => {
          console.log('NPC selected for response:', data.npc_id);
        });
        
        socketInstance.on('disconnect', () => {
          console.log('Socket disconnected');
          setIsSocketConnected(false);
          setError('Connection lost. Trying to reconnect...');
        });
        
        // Cleanup on component unmount
        return () => {
          try {
            if (socketInstance.isConnected?.()) {
              socketInstance.leaveRoom?.(chatIdString);
            }
          } catch (err) {
            console.warn('Failed to leave room on cleanup:', err);
          }
          socketInstance.off('new-message', () => {});
          socketInstance.off('thinking', () => {});
          socketInstance.off('npc-selected', () => {});
          socketInstance.off('disconnect', () => {});
          socketInstance.off('connect', () => {});
        };
      } catch (error) {
        console.error('Error initializing socket:', error);
        setError('Failed to connect. Please refresh the page.');
        setIsSocketConnected(false);
      }
    };
    
    initSocket();
  }, [chatId, username]);
  
  // Load NPC details
  useEffect(() => {
    const loadNpcDetails = async () => {
      const details: Record<string, NpcDetail> = {};
      
      for (const npcId of participants.npcs) {
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
  }, [participants.npcs]);
  
  // Update active message based on timeline position
  useEffect(() => {
    if (messages.length === 0) return;
    
    if (timelinePosition === 1) {
      // At the newest message
      setActiveMessageIndex(null); // null means use the latest message
    } else if (timelinePosition === 0) {
      // At the oldest message
      setActiveMessageIndex(0);
    } else {
      // Calculate index based on position
      const index = Math.floor((messages.length - 1) * timelinePosition);
      setActiveMessageIndex(index);
    }
  }, [timelinePosition, messages.length]);
  
  // Handle scroll in message container to update timeline position
  const handleMessageScroll = (e: React.UIEvent<HTMLDivElement>) => {
    if (!messageContainerRef || messages.length <= 1) return;
    
    // Don't update timeline if user is currently dragging the slider
    if (isScrolling) return;
    
    const container = e.currentTarget;
    const scrollHeight = container.scrollHeight - container.clientHeight;
    
    if (scrollHeight <= 0) return;
    
    // Calculate position from scroll (0 = oldest, 1 = newest)
    // We need to invert the scroll position since scrollTop 0 is actually newest messages
    const scrollPosition = 1 - (container.scrollTop / scrollHeight);
    
    // Only update if the change is significant
    if (Math.abs(scrollPosition - timelinePosition) > 0.02) {
      setTimelinePosition(scrollPosition);
      
      // Calculate the active message index based on scroll position
      if (scrollPosition < 1) {
        const index = Math.floor((messages.length - 1) * scrollPosition);
        setActiveMessageIndex(index);
      } else {
        setActiveMessageIndex(null); // Latest message
      }
    }
  };
  
  // Sync message container scroll position when timeline changes
  useEffect(() => {
    if (!messageContainerRef || messages.length <= 1 || isScrolling) return;
    
    const scrollHeight = messageContainerRef.scrollHeight - messageContainerRef.clientHeight;
    
    if (scrollHeight <= 0) return;
    
    // Calculate where to scroll based on timeline position
    // Invert the position because scrollTop 0 is newest messages
    const scrollTop = (1 - timelinePosition) * scrollHeight;
    
    // Smooth scroll to position
    messageContainerRef.scrollTo({
      top: scrollTop,
      behavior: 'smooth'
    });
  }, [timelinePosition, isScrolling]);
  
  // Update the timeline slider handling to set isScrolling flag
  const handleTimelineStart = () => {
    setIsScrolling(true);
  };
  
  const handleTimelineEnd = () => {
    setIsScrolling(false);
  };
  
  const handleTimelineChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPosition = parseFloat(e.target.value);
    setTimelinePosition(newPosition);
  };
  
  // Add socket reconnection handling function
  const handleReconnect = async () => {
    try {
      console.log('🔄 Manual reconnection attempt...');
      const instance = await socketClient.init(username);
      const socketInstance = instance as any;
      setSocketClientInstance(socketInstance);
      
      console.log('🔄 Trying to join room after reconnection:', chatId);
      if (socketInstance) {
        try {
          const joinResult = socketInstance.joinRoom?.(String(chatId));
          console.log('Manual reconnection room join result:', joinResult ? 'success' : 'failure');
        } catch (err) {
          console.warn('Failed to join room on reconnect:', err);
        }
      }
      
      setError(null);
    } catch (error) {
      console.error('Reconnection failed:', error);
      setError('Reconnection failed. Please try again.');
    }
  };
  
  // Send message function
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (message.trim() === '' || isSending) return;
    
    try {
      setIsSending(true);
      
      // Create message object
      const timestamp = new Date();
      const messageObj: ChatMessage = {
        id: `local-${Date.now()}`,
        text: message,
        sender: username,
        isUser: true,
        timestamp
      };
      
      // Add message to UI
      setMessages(prevMessages => [...prevMessages, messageObj]);
      
      // Clear input
      setMessage('');
      
      // Check socket connection
      if (!socketClientInstance || !isSocketConnected) {
        console.error('No socket connection');
        setError('Connection lost. Please refresh the page.');
        setIsSending(false);
        return;
      }
      
      // 🔧 Fix: Use roomId directly as string (parseInt 제거)
      const roomId = String(chatId);
      
      // Send message via socket with error handling
      console.log(`Emitting send-message event for room ${roomId}`, messageObj);
      
      try {
        const socketInstance = socketClientInstance as any;
        socketInstance?.emit?.('send-message', {
          roomId: roomId,
          message: messageObj
        });
        
        setIsThinking(true);
        
        // Reset timeline to show latest message
        setTimelinePosition(1);
        setActiveMessageIndex(null);
      } catch (socketError) {
        console.error('Socket emit failed:', socketError);
        setError('Failed to send message via socket');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setError('Failed to send message');
    } finally {
      setIsSending(false);
    }
  };
  
  // Handle key press (Enter to send)
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };
  
  // Generate default avatar URL
  const getDefaultAvatar = (name: string) => {
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random&size=128&font-size=0.5`;
  };
  
  // Get user profile image
  const getUserProfileImage = (): string => {
    if (userProfilePicture && userProfilePicture.length > 0) {
      return userProfilePicture;
    }
    // 기본 아바타 URL
    return `/Profile.png`;
  };
  
  // Get NPC display name
  const getNpcDisplayName = (npcId: string): string => {
    if (npcDetails[npcId]) {
      return npcDetails[npcId].name;
    }
    return npcId;
  };
  
  // Get NPC profile image
  const getNpcProfileImage = (npcId: string): string => {
    if (npcDetails[npcId] && npcDetails[npcId].portrait_url) {
      return npcDetails[npcId].portrait_url;
    }
    const displayName = getNpcDisplayName(npcId);
    return getDefaultAvatar(displayName);
  };
  
  // Calculate positions on an elliptical orbit - NPCs only
  const calculateCirclePosition = (index: number, total: number, radius: number) => {
    // Important: In our coordinate system:
    // 0 degrees = right (3 o'clock)
    // 90 degrees = bottom (6 o'clock) - USER IS ALWAYS HERE
    // 180 degrees = left (9 o'clock)
    // 270 degrees = top (12 o'clock)
    
    // Calculate how many degrees each participant should be separated by
    // We exclude the user position (6 o'clock/90 degrees)
    const totalParticipants = total + 1; // Including user
    const degreesPerParticipant = 360 / totalParticipants;
    
    // Start from user position + one segment 
    // (skip user's position at 90 degrees/6 o'clock)
    let angle = (90 + degreesPerParticipant + (index * degreesPerParticipant)) % 360;
    
    // Convert angle to radians for calculation
    const angleInRadians = (angle * Math.PI) / 180;
    
    // Calculate position on ellipse
    const ellipseXRadius = radius * 2.8; // Further increased horizontal radius (was 2.2)
    const ellipseYRadius = radius * 0.95; // Vertical radius unchanged
    
    const x = ellipseXRadius * Math.cos(angleInRadians);
    const y = ellipseYRadius * Math.sin(angleInRadians);
    
    return { x, y, angle };
  };
  
  // Get user position - ALWAYS at bottom (6 o'clock)
  const getUserPosition = (radius: number) => {
    // User is positioned at 6 o'clock (90 degrees in our coordinate system)
    const angle = 90; // 90 degrees = 6 o'clock position
    const angleInRadians = (angle * Math.PI) / 180;
    
    // Use the same elliptical calculations as NPCs
    const ellipseXRadius = radius * 2.8; // Further increased horizontal radius (was 2.2)
    const ellipseYRadius = radius * 0.95; // Vertical radius unchanged
    
    const x = ellipseXRadius * Math.cos(angleInRadians);
    const y = ellipseYRadius * Math.sin(angleInRadians);
    
    return { x, y, angle };
  };
  
  // Get the active participant ID based on current message
  const getActiveSpeakerId = (): string | null => {
    if (!currentMessage) return null;
    
    if (currentMessage.isUser) {
      return currentMessage.sender;
    } else {
      return currentMessage.npc_id || currentMessage.sender;
    }
  };
  
  const activeSpeakerId = getActiveSpeakerId();
  
  // Add an auto-refresh function for messages
  useEffect(() => {
    if (chatId && username) {
      // Load messages on initial render
      const loadMessages = async () => {
        try {
          setIsLoadingRoom(true);
          
          // 초기 메시지가 이미 있는 경우 API 호출 생략
          if (initialMessages && initialMessages.length > 0) {
            console.log(`✅ Using ${initialMessages.length} initial messages from props`);
            setMessages(initialMessages);
            setIsLoadingRoom(false);
            return;
          }
          
          // 메시지가 없거나 빈 배열인 경우에만 API에서 메시지 로딩
          console.log(`🔄 Loading messages for chat ID: ${chatId} (${typeof chatId})`);
          
          // ID를 숫자로 확인
          if (typeof chatId !== 'number' || isNaN(chatId) || chatId <= 0) {
            console.error(`❌ Invalid chat ID: ${chatId}`);
            setError('Invalid chat room ID format');
            setIsLoadingRoom(false);
            return;
          }
          
          const apiUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/api/rooms`;
          const response = await fetch(`${apiUrl}?id=${chatId}`);
          
          if (!response.ok) {
            console.error(`❌ Failed to load room data: ${response.status} ${response.statusText}`);
            setError('Failed to load chat room. It may have been deleted.');
            setIsLoadingRoom(false);
            return;
          }
          
          const data = await response.json();
          console.log(`📝 API Response:`, data ? `Room found (title: ${data.title})` : 'Room not found');
          
          // data가 null이거나 undefined인 경우 체크
          if (!data) {
            console.error(`❌ No data returned from API for room ID: ${chatId}`);
            setError('Chat room not found or has been deleted.');
            setIsLoadingRoom(false);
            return;
          }
          
          // id 필드 확인
          if (data.id === undefined) {
            console.error(`❌ Response missing ID field for room ID: ${chatId}`);
            setError('Invalid room data received from server');
            setIsLoadingRoom(false);
            return;
          }
          
          // ID 일치 여부 확인 (숫자 변환)
          const responseId = Number(data.id);
          if (isNaN(responseId) || responseId !== chatId) {
            console.error(`❌ ID mismatch: requested=${chatId}, received=${data.id} (${responseId})`);
            setError('Incorrect chat room data loaded');
            setIsLoadingRoom(false);
            return;
          }
          
          // messages 필드가 없는 경우 체크
          if (!data.messages) {
            console.log(`⚠️ No messages field in room data for ID: ${chatId}, initializing empty array`);
            data.messages = [];
          }
          
          console.log(`✅ Loaded ${data.messages.length} messages from API`);
          
          try {
            // Sort messages by timestamp (null 체크 추가)
            const sortedMessages = data.messages.sort((a: ChatMessage, b: ChatMessage) => {
              return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
            });
            
            setMessages(sortedMessages);
            
            // Set timeline to latest message
            setTimelinePosition(1);
            setActiveMessageIndex(null);
          } catch (sortError) {
            console.error('❌ Error sorting messages:', sortError);
            // 정렬 실패 시 원본 메시지 그대로 사용
            setMessages(data.messages);
          }
        } catch (error) {
          console.error('❌ Error loading messages:', error);
          setError('Failed to load messages. Please try refreshing the page.');
        } finally {
          setIsLoadingRoom(false);
        }
      };
      
      loadMessages();
    }
  }, [chatId, username, initialMessages]);
  
  // Add a message change animation effect
  useEffect(() => {
    // When the active message changes, animate the message bubble
    const messageBubble = document.getElementById('message-bubble');
    if (messageBubble) {
      // Add a quick fade-out/fade-in animation
      messageBubble.style.opacity = '0';
      messageBubble.style.transform = 'scale(0.95)';
      
      setTimeout(() => {
        messageBubble.style.opacity = '1';
        messageBubble.style.transform = 'scale(1)';
      }, 150);
    }
  }, [activeMessageIndex, currentMessage]);
  
  // Update useEffect for window resize
  useEffect(() => {
    // Calculate the initial circle radius based on viewport size
    const calculateRadius = () => {
      const containerElement = document.getElementById('elliptical-table');
      let containerWidth = 0;
      let containerHeight = 0;
      
      if (containerElement) {
        containerWidth = containerElement.offsetWidth;
        containerHeight = containerElement.offsetHeight;
      } else {
        // Fallback if element not found
        containerWidth = Math.min(windowDimensions.width * 0.8, 600);
        containerHeight = Math.min(windowDimensions.height * 0.8, 600);
      }
      
      // Use the smaller dimension divided by 2 for the radius but increase to spread participants more
      return Math.min(containerWidth, containerHeight) / 2.5; // Decreased divisor (was 2.2) to increase base radius
    };
    
    // Set initial radius
    const newRadius = calculateRadius();
    setCircleRadius(newRadius);
    
    // Update dimensions and radius on window resize
    const handleResize = () => {
      const newDimensions = {
        width: window.innerWidth,
        height: window.innerHeight
      };
      setWindowDimensions(newDimensions);
      const newRadius = calculateRadius();
      setCircleRadius(newRadius);
    };
    
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', handleResize);
      window.addEventListener('orientationchange', handleResize);
      
      // Force a resize on initial load
      handleResize();
    }
    
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('resize', handleResize);
        window.removeEventListener('orientationchange', handleResize);
      }
    };
  }, []);
  
  // Get the last 3 messages for display
  const getLastMessages = () => {
    if (messages.length === 0) return [];
    
    // If timeline is at the latest position, show the last 3 messages
    if (timelinePosition === 1) {
      const end = messages.length;
      const start = Math.max(0, end - 3);
      return messages.slice(start).reverse(); // Reverse to have most recent first
    }
    
    // If viewing old messages, show the current message and up to 2 following ones
    if (activeMessageIndex !== null) {
      const start = activeMessageIndex;
      const end = Math.min(messages.length, start + 3);
      const messagesToShow = messages.slice(start, end);
      return messagesToShow.reverse(); // Reverse to have current message first
    }
    
    return [];
  };
  
  // Get opacity based on message recency (first: 1, second: 0.66, third: 0.33)
  const getMessageOpacity = (index: number) => {
    const opacities = [1, 0.66, 0.33];
    return opacities[Math.min(index, opacities.length - 1)];
  };
  
  // Get the position offset for a message based on its sender
  const getMessagePosition = (message: ChatMessage) => {
    if (!message) return { x: 0, y: 0 };
    
    const senderId = message.isUser ? username : (message.npc_id || message.sender);
    
    // For user messages - position toward the bottom
    if (message.isUser) {
      // Get user position at the bottom of the ellipse
      const userPosition = getUserPosition(circleRadius);
      // Calculate offset (40% toward the user position)
      const offsetX = userPosition.x * 0.4;
      const offsetY = userPosition.y * 0.4;
      
      return { x: offsetX, y: offsetY };
    }
    
    // For NPC messages
    const npcIndex = participants.npcs.findIndex(id => id === senderId);
    if (npcIndex === -1) return { x: 0, y: 0 };
    
    // Calculate position based on NPC's position in the ellipse
    const { angle } = calculateCirclePosition(
      npcIndex, 
      participants.npcs.length, 
      circleRadius
    );
    
    // Calculate offset (40% toward the speaker)
    const angleInRadians = (angle * Math.PI) / 180;
    // Use elliptical calculation for offset too
    const ellipseXRadius = circleRadius * 2.8 * 0.4; // 40% of horizontal radius
    const ellipseYRadius = circleRadius * 0.75 * 0.4; // 40% of vertical radius
    const offsetX = ellipseXRadius * Math.cos(angleInRadians);
    const offsetY = ellipseYRadius * Math.sin(angleInRadians);
    
    return { x: offsetX, y: offsetY };
  };
  
  // Handle end conversation button click
  const handleEndConversation = () => {
    setShowPodcastModal(true);
  };

  // Handle podcast modal close
  const handleCloseModal = () => {
    setShowPodcastModal(false);
  };

  // Handle podcast generation
  const handleCreatePodcast = async () => {
    setIsGeneratingPodcast(true);
    setPodcastProgress(5);

    try {
      // Prepare conversation data
      const conversationData = messages.map(msg => ({
        text: msg.text,
        speaker: msg.isUser ? 'user' : msg.npc_id || msg.sender,
        speakerName: msg.isUser ? 'User' : getNpcDisplayName(msg.npc_id || msg.sender),
        timestamp: msg.timestamp
      }));

      // Call podcast generation API
      const response = await fetch('/api/podcast/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation: conversationData,
          title: chatTitle,
          participants: participants.npcs.map(npcId => ({
            id: npcId,
            name: getNpcDisplayName(npcId)
          }))
        }),
      });

      setPodcastProgress(50);

      if (response.ok) {
        const data = await response.json();
        console.log('Podcast generated:', data);
        setPodcastProgress(100);
        
        // Redirect to podcast page
        setTimeout(() => {
          router.push('/podcast');
        }, 1500);
      } else {
        throw new Error('Failed to generate podcast');
      }
    } catch (error) {
      console.error('Error generating podcast:', error);
      setError('Failed to generate podcast. Please try again.');
      setIsGeneratingPodcast(false);
    }
  };
  
  return (
    <div className="fixed inset-0 bg-white flex flex-col w-full h-full overflow-hidden">
      {/* Chat header with End Conversation button */}
      <div className="bg-white border-b border-gray-200 p-3 flex flex-col items-center relative">
        {/* Back button */}
        <button 
          onClick={onBack}
          style={{ 
            position: 'absolute', 
            left: '16px', 
            top: '16px', 
            background: 'none',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
            fontSize: '18px',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            backgroundColor: '#f3f4f6'
          }}
          className="text-gray-500 hover:text-gray-800 flex items-center justify-center"
        >
          <ArrowLeftIcon className="h-4 w-4 text-gray-700" />
        </button>

        {/* Centered chat title and participants */}
        <div className="text-center mx-auto">
          <h2 className="font-semibold text-gray-900">{chatTitle}</h2>
          <p className="text-xs text-gray-500 mt-1">
            with {participants.npcs.map(npcId => getNpcDisplayName(npcId)).join(', ')}
          </p>
        </div>
        
        {/* Right area with connection status and End Conversation button */}
        <div 
          style={{ 
            position: 'absolute', 
            right: '16px', 
            top: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          {/* Connection status indicator */}
          <div className={`w-2.5 h-2.5 rounded-full ${isSocketConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          
          {!isSocketConnected && (
            <button 
              onClick={handleReconnect}
              className="ml-2 text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
            >
              Reconnect
            </button>
          )}
          
          {/* End Conversation button */}
          <button 
            onClick={handleEndConversation}
            className="ml-2 text-xs px-2 py-1.5 bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors flex items-center"
          >
            <StopIcon className="h-3 w-3 mr-1" />
            End
          </button>
        </div>
      </div>
      
      {/* Error message display */}
      {error && (
        <div className="bg-red-50 text-red-700 p-3 text-sm text-center border-b border-red-100">
          <div className="font-semibold mb-1">Error</div>
          <div>{error}</div>
          <button 
            onClick={onBack}
            className="mt-2 px-4 py-1 bg-red-600 text-white rounded hover:bg-red-700 transition-colors inline-flex items-center"
          >
            <ArrowLeftIcon className="h-3 w-3 mr-1" />
            Back to Open Chat
          </button>
        </div>
      )}

      {/* Loading state */}
      {isLoadingRoom && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin mb-2"></div>
            <div className="text-gray-500">Loading conversation...</div>
          </div>
        </div>
      )}

      {/* Main circular chat area - only show when not loading and no error */}
      {!isLoadingRoom && !error && (
        <div className="flex-1 relative overflow-hidden flex items-center justify-center">
          {/* Circle layout with participants */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div 
              id="elliptical-table"
              className="relative" 
              style={{ 
                width: '80vmin', 
                height: '80vmin',
                maxWidth: '600px',
                maxHeight: '600px'
              }}
            >
              {/* Add the 3D table visualization - matched to participant orbit */}
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none" 
                style={{ 
                  width: `${circleRadius * 2.8 * 2}px`,
                  height: `${circleRadius * 0.95 * 2}px`,
                  borderRadius: '50%',
                  background: 'radial-gradient(ellipse at center, rgba(255,255,255,0.9) 0%, rgba(249,250,251,0.6) 60%, rgba(249,250,251,0) 100%)',
                  boxShadow: 'inset 0 0 20px rgba(0,0,0,0.05)',
                  zIndex: 5
                }}
              >
                {/* Table effect - subtle concentric ellipses */}
                <div 
                  style={{ 
                    position: 'absolute', 
                    top: '5%', 
                    left: '5%', 
                    right: '5%', 
                    bottom: '5%', 
                    borderRadius: '50%', 
                    border: '1px solid rgba(229, 231, 235, 0.3)'
                  }}
                ></div>
                <div 
                  style={{ 
                    position: 'absolute', 
                    top: '15%', 
                    left: '15%', 
                    right: '15%', 
                    bottom: '15%', 
                    borderRadius: '50%', 
                    border: '1px solid rgba(229, 231, 235, 0.3)'
                  }}
                ></div>
                <div 
                  style={{ 
                    position: 'absolute', 
                    top: '25%', 
                    left: '25%', 
                    right: '25%', 
                    bottom: '25%', 
                    borderRadius: '50%', 
                    border: '1px solid rgba(229, 231, 235, 0.3)'
                  }}
                ></div>
              </div>
              
              {/* Message bubbles - now showing multiple messages */}
              {getLastMessages().map((msg, index) => {
                const position = getMessagePosition(msg);
                const opacity = getMessageOpacity(index);
                const isActive = index === 0; // First message is active
                
                return (
                  <div 
                    key={`message-${msg.id}`}
                    className={`absolute z-20 transition-all duration-300 ease-in-out`}
                    style={{ 
                      top: `calc(50% + ${position.y}px)`,
                      left: `calc(50% + ${position.x}px)`,
                      transform: `translate(-50%, -50%) scale(${1 - index * 0.05})`,
                      opacity: opacity,
                      zIndex: 20 - index,
                      maxWidth: windowDimensions.width < 768 ? '85%' : '70%',
                      width: windowDimensions.width < 768 ? '85%' : '70%',
                      maxHeight: windowDimensions.width < 768 ? '35%' : '40%',
                    }}
                  >
                    <div 
                      className="overflow-auto"
                      style={{ 
                        border: isActive ? '2px solid #e5e7eb' : '1px solid #e5e7eb',
                        padding: windowDimensions.width < 768 ? '12px' : '24px',
                        transition: 'all 0.15s ease',
                        backgroundColor: '#ffffff',
                        boxShadow: '0 8px 20px rgba(0, 0, 0, 0.15)',
                        backdropFilter: 'blur(0)',
                        borderRadius: '16px',
                      }}
                      ref={isActive ? setMessageContainerRef : null}
                      onScroll={isActive ? handleMessageScroll : undefined}
                    >
                      <div className="font-semibold mb-2">
                        {msg.isUser 
                          ? (msg.sender === username ? 'User' : msg.sender)
                          : (msg.senderName || getNpcDisplayName(msg.npc_id || msg.sender))
                        }
                      </div>
                      <div className="text-gray-800">
                        {msg.text}
                      </div>
                      <div className="text-xs text-gray-500 mt-2 text-right">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                );
              })}
              
              {messages.length === 0 && (
                <div 
                  className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10"
                  style={{ 
                    maxHeight: windowDimensions.width < 768 ? '35%' : '40%', 
                    overflow: 'auto',
                    border: '2px solid #e5e7eb',
                    width: windowDimensions.width < 768 ? '85%' : '70%',
                    maxWidth: '500px',
                    padding: windowDimensions.width < 768 ? '12px' : '24px',
                    backgroundColor: '#ffffff',
                    boxShadow: '0 8px 20px rgba(0, 0, 0, 0.15)',
                    backdropFilter: 'blur(0)',
                    borderRadius: '16px',
                  }}
                  ref={setMessageContainerRef}
                >
                  <div className="text-gray-500 italic text-center">
                    No messages yet. Start the conversation!
                  </div>
                </div>
              )}
              
              {/* Render NPCs in a circle - optimized positioning */}
              {participants.npcs.map((npcId, index) => {
                const position = calculateCirclePosition(
                  index, 
                  participants.npcs.length, 
                  circleRadius
                );
                
                const isActive = npcId === activeSpeakerId;
                
                return (
                  <div 
                    key={npcId}
                    id={`npc-${npcId}`}
                    style={{
                      position: 'absolute',
                      left: '50%',
                      top: '50%',
                      transform: `translate(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px))`,
                      zIndex: isActive ? 20 : 10,
                      opacity: isActive ? 1 : 0.8,
                      transition: 'all 0.5s ease-in-out'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      transform: isActive ? 'scale(1.1)' : 'scale(1)',
                      transition: 'transform 0.3s ease'
                    }}>
                      <div style={{
                        width: windowDimensions.width < 768 ? '50px' : '70px',
                        height: windowDimensions.width < 768 ? '50px' : '70px',
                        borderRadius: '50%',
                        overflow: 'hidden',
                        border: isActive ? '4px solid #3b82f6' : '4px solid #e5e7eb',
                        boxShadow: isActive ? '0 10px 15px -3px rgba(0, 0, 0, 0.1)' : 'none',
                        transition: 'border-color 0.3s ease, box-shadow 0.3s ease'
                      }}>
                        <img 
                          src={getNpcProfileImage(npcId)}
                          alt={getNpcDisplayName(npcId)}
                          style={{ 
                            objectFit: 'cover',
                            objectPosition: 'center',
                            width: '100%',
                            height: '100%',
                            filter: isActive ? 'none' : 'brightness(0.7) grayscale(30%)',
                            transition: 'filter 0.3s ease'
                          }}
                          onError={(e) => {
                            console.error("NPC image loading error:", e);
                            const target = e.target as HTMLImageElement;
                            target.onerror = null; // 무한 루프 방지
                            target.src = getDefaultAvatar(getNpcDisplayName(npcId));
                          }}
                        />
                      </div>
                      <div style={{
                        fontSize: windowDimensions.width < 768 ? '0.75rem' : '0.875rem',
                        marginTop: '8px',
                        fontWeight: 500,
                        color: isActive ? '#000000' : '#6b7280',
                        textAlign: 'center',
                        maxWidth: '100px',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        transition: 'color 0.3s ease'
                      }}>
                        {getNpcDisplayName(npcId)}
                      </div>
                    </div>
                  </div>
                );
              })}
              
              {/* User at the bottom - optimized positioning */}
              <div 
                id="user-avatar"
                style={{
                  position: 'absolute',
                  left: '50%',
                  top: '50%',
                  transform: `translate(calc(-50% + ${getUserPosition(circleRadius).x}px), calc(-50% + ${getUserPosition(circleRadius).y}px))`,
                  zIndex: username === activeSpeakerId ? 20 : 10,
                  opacity: username === activeSpeakerId ? 1 : 0.8,
                  transition: 'all 0.5s ease-in-out'
                }}
              >
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  transform: username === activeSpeakerId ? 'scale(1.1)' : 'scale(1)',
                  transition: 'transform 0.3s ease'
                }}>
                  <div style={{
                    width: windowDimensions.width < 768 ? '50px' : '70px',
                    height: windowDimensions.width < 768 ? '50px' : '70px',
                    borderRadius: '50%',
                    overflow: 'hidden',
                    border: username === activeSpeakerId ? '4px solid #3b82f6' : '4px solid #e5e7eb',
                    boxShadow: username === activeSpeakerId ? '0 10px 15px -3px rgba(0, 0, 0, 0.1)' : 'none',
                    transition: 'border-color 0.3s ease, box-shadow 0.3s ease'
                  }}>
                    <img 
                      src={getUserProfileImage()}
                      alt="User"
                      style={{ 
                        objectFit: 'cover',
                        width: '100%',
                        height: '100%',
                        filter: username === activeSpeakerId ? 'none' : 'brightness(0.7) grayscale(30%)',
                        transition: 'filter 0.3s ease'
                      }}
                      onError={(e) => {
                        console.error("Profile image loading error:", e);
                        const target = e.target as HTMLImageElement;
                        target.onerror = null; // 무한 루프 방지
                        target.src = getDefaultAvatar(username || 'User');
                      }}
                    />
                  </div>
                  <div style={{
                    fontSize: windowDimensions.width < 768 ? '0.75rem' : '0.875rem',
                    marginTop: '8px',
                    fontWeight: 500,
                    color: username === activeSpeakerId ? '#000000' : '#6b7280',
                    textAlign: 'center',
                    transition: 'color 0.3s ease'
                  }}>
                    User
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Timeline controls - only show when not loading and no error */}
      {!isLoadingRoom && !error && (
        <div className="w-full flex-none flex items-center justify-center py-4">
          <div className="max-w-md w-full px-4">
            <div className="relative">
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={timelinePosition}
                onChange={handleTimelineChange}
                onMouseDown={handleTimelineStart}
                onTouchStart={handleTimelineStart}
                onMouseUp={handleTimelineEnd}
                onTouchEnd={handleTimelineEnd}
                className="w-full slider-thumb"
                style={{
                  height: '6px',
                  appearance: 'none',
                  borderRadius: '3px',
                  background: 'linear-gradient(to right, #3b82f6, #93c5fd)',
                  outline: 'none',
                }}
              />
            </div>
            <div className="text-center text-sm text-gray-500 mt-2">
              {timelinePosition < 1 && activeMessageIndex !== null && (
                <div>
                  Viewing past messages {activeMessageIndex !== null 
                    ? `(${activeMessageIndex + 1} of ${messages.length})`
                    : `(${messages.length})`}
                </div>
              )}
              {timelinePosition === 1 && messages.length > 0 && (
                <div>Latest message</div>
              )}
              {messages.length === 0 && (
                <div>No messages yet</div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Input area - only show when not loading and no error */}
      {!isLoadingRoom && !error && (
        <div className="bg-white border-t border-gray-200 p-3 w-full" style={{ paddingBottom: '16px' }}>
          <form onSubmit={handleSendMessage} style={{
            maxWidth: '95%',
            margin: '0 auto',
            padding: '0 8px'
          }}>
            <div 
              style={{
                position: 'relative',
                width: '95%', 
                backgroundColor: '#f8f8f8',
                borderRadius: '24px',
                padding: '8px 16px',
                marginTop: '8px',
                display: 'flex',
                alignItems: 'flex-end',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
                zIndex: 10
              }}
            >
              <textarea
                ref={inputRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Type a message (Press Enter to send)"
                style={{
                  flexGrow: 1,
                  minHeight: '36px',
                  maxHeight: '120px',
                  background: 'transparent',
                  border: 'none',
                  resize: 'none',
                  padding: '8px 0',
                  outline: 'none',
                  fontSize: '14px',
                  lineHeight: 1.5
                }}
                disabled={!isSocketConnected || isSending || isThinking || error !== null}
              />
              <button
                type="submit"
                style={{
                  flexShrink: 0,
                  backgroundColor: message.trim() === '' || !isSocketConnected || isSending || isThinking || error !== null ? '#e0e0e0' : '#0084ff',
                  color: message.trim() === '' || !isSocketConnected || isSending || isThinking || error !== null ? '#a0a0a0' : 'white',
                  borderRadius: '50%',
                  width: '36px',
                  height: '36px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginLeft: '8px',
                  transition: 'all 0.2s',
                  border: 'none',
                  cursor: message.trim() === '' || !isSocketConnected || isSending || isThinking || error !== null ? 'not-allowed' : 'pointer',
                  opacity: message.trim() === '' || !isSocketConnected || isSending || isThinking || error !== null ? 0.5 : 1
                }}
                disabled={message.trim() === '' || !isSocketConnected || isSending || isThinking || error !== null}
              >
                {isSending ? (
                  <div style={{
                    width: '20px',
                    height: '20px',
                    border: '2px solid white',
                    borderTopColor: 'transparent',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }}></div>
                ) : (
                  <PaperAirplaneIcon className="h-5 w-5" />
                )}
              </button>
            </div>
          </form>
          
          {/* Thinking indicator - below textarea */}
          {isThinking && (
            <div className="text-xs text-gray-500 mt-1 text-center">
              <span className="inline-block w-5 h-3 relative overflow-hidden mr-1">
                <span className="absolute w-1 h-1 bg-gray-500 rounded-full animate-bounce" style={{ left: '0%', animationDelay: '0s' }}></span>
                <span className="absolute w-1 h-1 bg-gray-500 rounded-full animate-bounce" style={{ left: '33%', animationDelay: '0.2s' }}></span>
                <span className="absolute w-1 h-1 bg-gray-500 rounded-full animate-bounce" style={{ left: '66%', animationDelay: '0.4s' }}></span>
              </span>
              Thinking...
            </div>
          )}
        </div>
      )}

      {/* Podcast generation modal */}
      {showPodcastModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            {!isGeneratingPodcast ? (
              <>
                <h3 className="text-xl font-semibold mb-4">Create Podcast</h3>
                <p className="mb-6">
                  Would you like to create a podcast from this conversation? 
                  This will generate audio for all messages in this chat.
                </p>
                <div className="flex justify-end space-x-3">
                  <button
                    onClick={handleCloseModal}
                    className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-100 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreatePodcast}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                  >
                    Create Podcast
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center py-4">
                <h3 className="text-xl font-semibold mb-6">Generating Podcast</h3>
                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out" 
                    style={{ width: `${podcastProgress}%` }}
                  ></div>
                </div>
                <p className="text-gray-600">
                  {podcastProgress < 100 
                    ? 'Please wait while we create your podcast...' 
                    : 'Podcast created successfully! Redirecting...'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CircularChatUI;