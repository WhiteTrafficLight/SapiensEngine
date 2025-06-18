import React, { useState } from 'react';
import { UserIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { ChatRoomListProps, ChatRoom } from '../types/openChat.types';

const ChatRoomList: React.FC<ChatRoomListProps> = ({
  chatRooms,
  isLoading,
  onRefresh,
  onJoinChat
}) => {
  const [showParticipants, setShowParticipants] = useState<number | null>(null);

  // 채팅 타입별로 분류
  const dialogueTypes = [
    { key: 'free', title: 'Free Discussion', color: 'bg-blue-50 border-blue-200' },
    { key: 'debate', title: 'Pro-Con Debate', color: 'bg-red-50 border-red-200' },
    { key: 'socratic', title: 'Socratic Dialogue', color: 'bg-green-50 border-green-200' },
    { key: 'dialectical', title: 'Dialectical Discussion', color: 'bg-purple-50 border-purple-200' }
  ];

  // 타입별로 채팅방 필터링
  const getChatsByType = (type: string) => {
    return chatRooms.filter(chat => chat.dialogueType === type);
  };

  const handleChatClick = (chat: ChatRoom) => {
    onJoinChat(chat.id);
  };

  const renderChatCard = (chat: ChatRoom) => (
    <div 
      key={`chat-${chat.id}`} 
      className="chat-room-card"
      onClick={() => handleChatClick(chat)}
    >
      <div className="flex items-center justify-between">
        <h4 className="chat-room-card-title flex-1">{chat.title}</h4>
        
        <button 
          onClick={(e) => {
            e.stopPropagation();
            const chatIdNum = typeof chat.id === 'string' ? parseInt(chat.id) : chat.id;
            setShowParticipants(showParticipants === chatIdNum ? null : chatIdNum);
          }}
          className="chat-room-card-details-btn"
        >
          Details
        </button>
      </div>
      
      {/* Participants dropdown */}
      {showParticipants === (typeof chat.id === 'string' ? parseInt(chat.id) : chat.id) && (
        <div className="chat-room-card-dropdown">
          <div className="flex justify-between items-center mb-1">
            <span className="font-medium">Participants</span>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                setShowParticipants(null);
              }}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>
          <div className="grid grid-cols-2 gap-1">
            <div>
              <div className="font-medium text-gray-700">Users</div>
              {chat.participants.users.map(user => (
                <div key={user} className="text-gray-600">{user}</div>
              ))}
            </div>
            <div>
              <div className="font-medium text-gray-700">NPCs</div>
              {chat.participants.npcs.map(npc => (
                <div key={npc} className="text-gray-600">{npc}</div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (isLoading && chatRooms.length === 0) {
    return (
      <div className="py-20">
        <div className="spinner-large mx-auto"></div>
        <p className="text-center mt-4 text-gray-500">Loading chats...</p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* 4개 섹션 그리드 - 정확히 4등분 */}
      <div className="flex-1 grid grid-cols-2 grid-rows-2 gap-4 p-4 overflow-hidden">
        {dialogueTypes.map((dialogueType) => {
          const chatsForType = getChatsByType(dialogueType.key);
          
          return (
            <div 
              key={dialogueType.key}
              className="flex flex-col bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden h-full"
            >
              {/* 섹션 타이틀 */}
              <div className={`flex-shrink-0 p-3 border-b border-gray-200 ${dialogueType.color} rounded-t-lg`}>
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-sm text-gray-800">{dialogueType.title}</h3>
                  <span className="text-xs text-gray-600">({chatsForType.length} rooms)</span>
                </div>
              </div>
              
              {/* 스크롤 가능한 채팅방 목록 */}
              <div className="flex-1 overflow-y-auto p-2">
                {chatsForType.length > 0 ? (
                  chatsForType.map(chat => renderChatCard(chat))
                ) : (
                  <div className="text-center py-8">
                    <p className="text-xs text-gray-500">
                      No {dialogueType.title.toLowerCase()} rooms found
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ChatRoomList; 