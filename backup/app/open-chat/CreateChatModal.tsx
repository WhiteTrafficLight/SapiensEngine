'use client';

import React, { useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface CreateChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (params: {
    title: string;
    description: string;
    npcs: string[];
    isPublic: boolean;
  }) => void;
}

const CreateChatModal: React.FC<CreateChatModalProps> = ({ isOpen, onClose, onCreate }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const [selectedNPCs, setSelectedNPCs] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Available philosophers for selection
  const availableNPCs = [
    'Albert Camus',
    'Jean-Paul Sartre',
    'Friedrich Nietzsche',
    'Simone de Beauvoir',
    'Socrates',
    'Plato',
    'Aristotle',
    'Confucius',
  ];

  // Toggle selection of an NPC
  const toggleNPC = (npc: string) => {
    if (selectedNPCs.includes(npc)) {
      setSelectedNPCs(selectedNPCs.filter(n => n !== npc));
    } else {
      setSelectedNPCs([...selectedNPCs, npc]);
    }
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || selectedNPCs.length === 0) return;

    setIsSubmitting(true);
    
    onCreate({
      title: title.trim(),
      description: description.trim(),
      npcs: selectedNPCs,
      isPublic
    });
    
    // Reset form (will only be visible if the modal doesn't close)
    resetForm();
  };

  // Reset form fields
  const resetForm = () => {
    setTitle('');
    setDescription('');
    setSelectedNPCs([]);
    setIsPublic(true);
    setIsSubmitting(false);
  };

  // Close modal and reset form
  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop overlay */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-70 backdrop-blur-sm z-[9000]"
        onClick={handleClose}
      ></div>
      
      {/* Modal container */}
      <div 
        className="fixed w-[95%] sm:w-[90%] md:w-[85%] max-w-[700px] max-h-[90vh] bg-white rounded-xl z-[9001] overflow-hidden"
        style={{ 
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50 rounded-t-xl">
          <h2 className="text-xl font-semibold text-gray-900">Create New Chat</h2>
          <button 
            onClick={handleClose}
            className="text-gray-500 hover:text-gray-700 transition-colors p-1 rounded-full hover:bg-gray-200"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>
        
        {/* Modal content */}
        <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 70px)' }}>
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block mb-2 text-sm font-medium text-gray-700">Chat Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter a philosophical topic..."
                className="w-full p-3 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>
            
            <div className="mb-4">
              <label className="block mb-2 text-sm font-medium text-gray-700">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Provide some context for the discussion..."
                className="w-full p-3 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent h-24"
              />
            </div>
            
            <div className="mb-4">
              <label className="block mb-2 text-sm font-medium text-gray-700">Privacy</label>
              <div className="flex items-center space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={isPublic}
                    onChange={() => setIsPublic(true)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Public</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={!isPublic}
                    onChange={() => setIsPublic(false)}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Private</span>
                </label>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {isPublic 
                  ? 'Public chats are visible to everyone and appear in the chat list.' 
                  : 'Private chats are only visible to participants.'}
              </p>
            </div>
            
            <div className="mb-6">
              <label className="block mb-2 text-sm font-medium text-gray-700">Select Philosophers</label>
              
              {/* Selected NPCs display */}
              {selectedNPCs.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-3">
                  {selectedNPCs.map((npc) => (
                    <div 
                      key={`selected-${npc}`}
                      className="flex items-center bg-blue-100 text-blue-800 px-2 py-1 rounded-lg text-sm"
                    >
                      <span>{npc}</span>
                      <button 
                        type="button"
                        onClick={() => toggleNPC(npc)}
                        className="ml-1 text-blue-600 hover:text-blue-800"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              {/* NPC selection grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 mt-2 border border-gray-200 rounded-lg p-3 bg-gray-50">
                {availableNPCs.map((npc) => (
                  <div 
                    key={npc}
                    onClick={() => toggleNPC(npc)}
                    className={`border p-2 rounded-lg cursor-pointer text-center transition-all text-sm ${
                      selectedNPCs.includes(npc) 
                        ? 'bg-blue-600 text-white border-blue-600' 
                        : 'bg-white hover:bg-gray-100 border-gray-300'
                    }`}
                  >
                    {npc}
                  </div>
                ))}
              </div>
              <p className="mt-1 text-xs text-gray-500">Select the philosophers you want to chat with.</p>
            </div>
            
            {/* Modal footer */}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                disabled={!title.trim() || selectedNPCs.length === 0 || isSubmitting}
              >
                {isSubmitting ? (
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
      </div>
    </>
  );
};

export default CreateChatModal; 