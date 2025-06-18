import React, { useState } from 'react';
import { PlusIcon } from '@heroicons/react/24/outline';
import { useOpenChatState } from '../hooks/useOpenChatState';
import SocketStatusIndicator from './SocketStatusIndicator';
import ChatRoomList from './ChatRoomList';
import CreateChatModal from './CreateChatModal';

const OpenChatContainer: React.FC = () => {
  const [showTooltip, setShowTooltip] = useState(false);
  
  const {
    // State
    activeChats,
    isLoading,
    showCreateChatModal,
    socketConnected,
    username,
    philosophers,
    customNpcs,
    isCreating,
    
    // Actions
    updateState,
    loadChatRooms,
    initializeSocket,
    handleCreateChat,
    handleJoinChat,
  } = useOpenChatState();

  const handleCreateChatClick = () => {
    updateState({ showCreateChatModal: true });
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Socket Status */}
      <SocketStatusIndicator 
        connected={socketConnected} 
        onReconnect={initializeSocket}
      />
      
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold">Open Philosophical Dialogues</h1>
          <div className="flex items-center gap-4">
            {/* Create Chat Button */}
            <div className="relative">
              <button 
                onClick={handleCreateChatClick}
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                disabled={isCreating}
                className="btn-create-chat"
                aria-label="Create New Chat"
              >
                <PlusIcon className="icon" />
              </button>
              
              {/* Tooltip */}
              <div 
                className={`btn-create-chat-tooltip ${showTooltip ? '' : 'hidden'}`}
              >
                Create New Chat
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Chat Room List */}
      <div className="flex-1 overflow-hidden">
        <ChatRoomList
          chatRooms={activeChats}
          isLoading={isLoading}
          onRefresh={loadChatRooms}
          onJoinChat={handleJoinChat}
        />
      </div>
      
      {/* Create Chat Modal */}
      <CreateChatModal
        isOpen={showCreateChatModal}
        onClose={() => updateState({ showCreateChatModal: false })}
        onCreateChat={handleCreateChat}
        isCreating={isCreating}
        philosophers={philosophers}
        customNpcs={customNpcs}
      />
    </div>
  );
};

export default OpenChatContainer; 