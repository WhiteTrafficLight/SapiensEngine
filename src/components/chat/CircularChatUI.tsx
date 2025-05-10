import React, { useEffect, useState } from 'react';

// Add an auto-refresh function for messages
useEffect(() => {
  if (chatId && username) {
    // Load messages on initial render
    const loadMessages = async () => {
      try {
        // 안전한 null 체크 추가: messages가 없거나 비어있는 경우만 로드
        if (!messages || messages.length === 0) {
          console.log('Loading messages for chat:', chatId);
          const apiUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/api/rooms`;
          const response = await fetch(`${apiUrl}?id=${chatId}`);
          
          if (response.ok) {
            const data = await response.json();
            console.log(`Loaded ${data.messages?.length} messages from API`);
            
            // Sort messages by timestamp (null 체크 추가)
            const sortedMessages = data.messages?.sort((a: ChatMessage, b: ChatMessage) => {
              return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
            }) || [];
            
            setMessages(sortedMessages);
            
            // Set timeline to latest message
            setTimelinePosition(1);
            setActiveMessageIndex(null);
          }
        }
      } catch (error) {
        console.error('Error loading messages:', error);
      }
    };
    
    loadMessages();
  }
}, [chatId, username, messages?.length]); 