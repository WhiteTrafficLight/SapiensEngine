'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ChatUI from '@/components/chat/ChatUI';
import chatService, { ChatRoom } from '@/lib/ai/chatService';

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chatId = searchParams.get('id');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatData, setChatData] = useState<ChatRoom | null>(null);

  useEffect(() => {
    if (!chatId) {
      setError('No chat ID provided');
      setLoading(false);
      return;
    }

    const loadChatData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const room = await chatService.getChatRoomById(chatId);
        
        if (!room) {
          setError('Chat room not found');
          return;
        }
        
        // Check if room has any users (excluding NPCs)
        if (room.participants.users.length === 0) {
          // No users left in the chat room, redirect to open chat page
          router.push('/open-chat');
          return;
        }
        
        setChatData(room);
      } catch (error) {
        console.error('Failed to load chat:', error);
        setError('Failed to load chat data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    loadChatData();
  }, [chatId, router]);

  const handleBackToOpenChat = () => {
    router.push('/open-chat');
  };

  return (
    <div className="h-screen w-screen">
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
        <ChatUI 
          chatId={chatData.id}
          chatTitle={chatData.title}
          participants={chatData.participants}
          initialMessages={chatData.messages}
          onBack={() => {
            // You can perform any cleanup or save data here before navigating back
            router.push('/open-chat');
          }}
        />
      ) : (
        <div className="flex h-full justify-center items-center">
          <p className="text-xl text-gray-500">Chat not found</p>
        </div>
      )}
    </div>
  );
} 