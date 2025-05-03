'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  PlusCircleIcon, 
  MagnifyingGlassIcon, 
  ChatBubbleLeftRightIcon,
  UserCircleIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import chatService, { ChatRoom } from '@/lib/ai/chatService';
import CreateChatModal from './CreateChatModal';

export default function OpenChatPage() {
  const router = useRouter();
  const [chatRooms, setChatRooms] = useState<ChatRoom[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateChatModal, setShowCreateChatModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [username, setUsername] = useState<string>('');
  
  // Fetch all available chat rooms
  const fetchChatRooms = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Get random username if not set (this would be replaced with real auth)
      const currentUsername = username || generateRandomUsername();
      if (!username) setUsername(currentUsername);
      
      // Fetch rooms with the username to see both public and private rooms they can access
      const rooms = await chatService.getChatRooms(currentUsername);
      setChatRooms(rooms);
    } catch (err) {
      console.error('Failed to fetch chat rooms:', err);
      setError('Failed to load chat rooms. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Generate a random username for this session
  const generateRandomUsername = () => {
    const savedUsername = localStorage.getItem('agoramind-username');
    if (savedUsername) return savedUsername;
    
    const newUsername = `User${Math.floor(Math.random() * 10000)}`;
    localStorage.setItem('agoramind-username', newUsername);
    return newUsername;
  };

  // Initial load
  useEffect(() => {
    fetchChatRooms();
    
    // Get username from localStorage or generate a new one
    const savedUsername = localStorage.getItem('agoramind-username');
    if (savedUsername) {
      setUsername(savedUsername);
    } else {
      const newUsername = generateRandomUsername();
      setUsername(newUsername);
    }
  }, []);

  // Handle creating a new chat
  const handleCreateChat = async (params: {
    title: string;
    description: string;
    npcs: string[];
    isPublic: boolean;
  }) => {
    try {
      setIsLoading(true);
      
      // Add the current user as creator and participant
      const chatRoomParams = {
        title: params.title,
        description: params.description,
        creator: username,
        participants: {
          users: [username],
          npcs: params.npcs
        },
        isPublic: params.isPublic
      };
      
      const newRoom = await chatService.createChatRoom(chatRoomParams);
      
      // Navigate to the new chat room
      router.push(`/chat/${newRoom.id}`);
    } catch (err) {
      console.error('Failed to create chat room:', err);
      setError('Failed to create the chat room. Please try again.');
      setIsLoading(false);
      setShowCreateChatModal(false);
    }
  };

  // Handle joining an existing chat
  const handleJoinChat = (roomId: string | number) => {
    // Add the user to the chat room participants first
    chatService.addParticipant(roomId, username, false)
      .then(() => {
        router.push(`/chat/${roomId}`);
      })
      .catch(err => {
        console.error('Failed to join chat room:', err);
        setError('Failed to join the chat room. Please try again.');
      });
  };

  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  // Filter chat rooms based on search query
  const filteredChatRooms = chatRooms.filter(room => 
    room.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (room.description && room.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // Format date to relative time
  const formatRelativeTime = (date: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - new Date(date).getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return new Date(date).toLocaleDateString();
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Open Chats</h1>
          <p className="text-sm text-gray-600">
            Join existing philosophical discussions or create your own
          </p>
        </div>
        <div className="flex items-center">
          <button 
            onClick={fetchChatRooms}
            className="p-2 mr-2 rounded-full text-gray-600 hover:bg-gray-100"
            aria-label="Refresh chat rooms"
            title="Refresh chat rooms"
          >
            <ArrowPathIcon className="h-5 w-5" />
          </button>
          <button
            onClick={() => setShowCreateChatModal(true)}
            className="flex items-center bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <PlusCircleIcon className="h-5 w-5 mr-2" />
            <span>Create Chat</span>
          </button>
        </div>
      </div>
      
      {/* Username display */}
      <div className="mb-6 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center">
          <UserCircleIcon className="h-6 w-6 text-gray-500 mr-2" />
          <div>
            <p className="text-sm text-gray-600">You are logged in as:</p>
            <p className="font-medium text-gray-800">{username}</p>
          </div>
        </div>
      </div>
      
      {/* Search bar */}
      <div className="mb-6 relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search for chats..."
          className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={searchQuery}
          onChange={handleSearchChange}
        />
      </div>
      
      {error && (
        <div className="mb-6 p-4 bg-red-50 text-red-800 rounded-lg">
          {error}
        </div>
      )}
      
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <>
          {filteredChatRooms.length === 0 ? (
            <div className="text-center py-12">
              <ChatBubbleLeftRightIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-semibold text-gray-900">No chat rooms found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchQuery ? 'Try a different search term or create a new chat' : 'Get started by creating a new chat room'}
              </p>
              <div className="mt-6">
                <button
                  onClick={() => setShowCreateChatModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none"
                >
                  <PlusCircleIcon className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                  Create New Chat
                </button>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {filteredChatRooms.map((room) => (
                <div 
                  key={room.id} 
                  className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden"
                >
                  <div className="p-4">
                    <div className="flex justify-between items-start">
                      <h3 className="font-semibold text-gray-900 text-lg">{room.title}</h3>
                      <span className="text-xs text-gray-500 flex items-center">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        {formatRelativeTime(room.lastActivity)}
                      </span>
                    </div>
                    {room.description && (
                      <p className="mt-1 text-sm text-gray-600 line-clamp-2">{room.description}</p>
                    )}
                    
                    <div className="mt-3 flex items-center text-xs text-gray-500">
                      <span className="flex items-center mr-4">
                        <UserCircleIcon className="h-4 w-4 mr-1" />
                        <span>
                          {room.participants.users.length === 1 
                            ? '1 user' 
                            : `${room.participants.users.length} users`}
                        </span>
                      </span>
                      <span>with {room.participants.npcs.join(', ')}</span>
                    </div>
                    
                    <div className="mt-4 flex justify-end">
                      {/* Show different buttons based on whether user is already a participant */}
                      {room.participants.users.includes(username) ? (
                        <button
                          onClick={() => router.push(`/chat/${room.id}`)}
                          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none"
                        >
                          Continue Chat
                        </button>
                      ) : (
                        <button
                          onClick={() => handleJoinChat(room.id)}
                          className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none"
                        >
                          Join Chat
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      
      {/* Create chat modal */}
      <CreateChatModal
        isOpen={showCreateChatModal}
        onClose={() => setShowCreateChatModal(false)}
        onCreate={handleCreateChat}
      />
    </div>
  );
}
