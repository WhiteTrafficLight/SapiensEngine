'use client';

import React, { useState } from 'react';
import chatService, { ChatRoomCreationParams } from '@/lib/ai/chatService';

export default function CreateChatPage() {
  const [newChatTitle, setNewChatTitle] = useState('');
  const [newChatContext, setNewChatContext] = useState('');
  const [maxParticipants, setMaxParticipants] = useState(5);
  const [selectedNPCs, setSelectedNPCs] = useState<string[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  
  // Sample available NPCs
  const availableNPCs = [
    'Socrates', 'Plato', 'Aristotle', 'Kant', 'Nietzsche', 
    'Sartre', 'Camus', 'Simone de Beauvoir', 'Marx', 'Rousseau',
    'Heidegger', 'Wittgenstein', 'Confucius', 'Lao Tzu', 'Buddha'
  ];
  
  // Toggle NPC selection
  const toggleNPC = (npc: string) => {
    if (selectedNPCs.includes(npc)) {
      setSelectedNPCs(selectedNPCs.filter(n => n !== npc));
    } else {
      setSelectedNPCs([...selectedNPCs, npc]);
    }
  };

  // Handle chat creation
  const handleCreateChat = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!newChatTitle.trim() || selectedNPCs.length === 0) return;
    
    try {
      setIsCreating(true);
      
      const chatParams: ChatRoomCreationParams = {
        title: newChatTitle,
        context: newChatContext,
        maxParticipants,
        npcs: selectedNPCs
      };
      
      const newChat = await chatService.createChatRoom(chatParams);
      
      // 채팅방 생성 후 부모 창을 채팅방으로 리다이렉트하고 현재 창은 닫기
      if (window.opener) {
        window.opener.location.href = `/chat?id=${newChat.id}`;
        window.close();
      } else {
        // 부모 창이 없는 경우 (직접 URL로 접근한 경우) 현재 창에서 이동
        window.location.href = `/chat?id=${newChat.id}`;
      }
    } catch (error) {
      console.error('Failed to create chat room:', error);
      alert('Failed to create chat room. Please try again.');
      setIsCreating(false);
    }
  };

  return (
    <div className="p-6 max-w-full">
      <h1 className="text-2xl font-bold mb-6">Create New Chat</h1>
      
      <form onSubmit={handleCreateChat}>
        <div className="mb-4">
          <label className="block mb-1 font-medium">Chat Title</label>
          <input
            type="text"
            value={newChatTitle}
            onChange={(e) => setNewChatTitle(e.target.value)}
            placeholder="Enter a philosophical topic..."
            className="w-full p-2 border border-black rounded-md"
            required
          />
        </div>
        
        <div className="mb-4">
          <label className="block mb-1 font-medium">Context</label>
          <textarea
            value={newChatContext}
            onChange={(e) => setNewChatContext(e.target.value)}
            placeholder="Provide some context for the discussion..."
            className="w-full p-2 border border-black rounded-md h-24"
          />
        </div>
        
        <div className="mb-4">
          <label className="block mb-1 font-medium">Maximum Participants</label>
          <input
            type="number"
            value={maxParticipants}
            onChange={(e) => setMaxParticipants(parseInt(e.target.value))}
            min="2"
            max="10"
            className="w-full p-2 border border-black rounded-md"
          />
        </div>
        
        <div className="mb-6">
          <label className="block mb-1 font-medium">Select NPCs</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-2">
            {availableNPCs.map(npc => (
              <div 
                key={npc}
                onClick={() => toggleNPC(npc)}
                className={`border p-2 rounded-md cursor-pointer text-center text-sm ${
                  selectedNPCs.includes(npc) 
                    ? 'bg-black text-white' 
                    : 'hover:bg-gray-100'
                }`}
              >
                {npc}
              </div>
            ))}
          </div>
        </div>
        
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => window.close()}
            className="px-4 py-2 border border-black rounded-md hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 bg-black text-white rounded-md hover:bg-gray-800 flex items-center"
            disabled={!newChatTitle.trim() || selectedNPCs.length === 0 || isCreating}
          >
            {isCreating ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                Creating...
              </>
            ) : (
              'Create Chat'
            )}
          </button>
        </div>
      </form>
    </div>
  );
} 