import React, { useState, useRef } from 'react';
import { XMarkIcon, DocumentArrowUpIcon } from '@heroicons/react/24/outline';
import { CreateChatModalProps, ChatRoomCreationParams } from '../types/openChat.types';
import PhilosopherDetailsModal from './PhilosopherDetailsModal';

interface Philosopher {
  id: string;
  name: string;
  period?: string; 
  nationality?: string;
  description?: string;
  key_concepts?: string[];
  portrait_url?: string;
}

const CreateChatModal: React.FC<CreateChatModalProps> = ({
  isOpen,
  onClose,
  onCreateChat,
  isCreating,
  philosophers,
  customNpcs
}) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [formData, setFormData] = useState<ChatRoomCreationParams>({
    title: '',
    maxParticipants: 6,
    npcs: [],
    isPublic: true,
    generateInitialMessage: true,
    dialogueType: 'free',
    context: '',
    contextUrl: '',
    contextFileContent: ''
  });

  const [contextType, setContextType] = useState<'none' | 'url' | 'file'>('none');
  const [selectedPhilosophers, setSelectedPhilosophers] = useState<string[]>([]);
  const [selectedCustomNpcs, setSelectedCustomNpcs] = useState<string[]>([]);
  const [npcPositions, setNpcPositions] = useState<Record<string, 'pro' | 'con'>>({});
  const [userDebateRole, setUserDebateRole] = useState<'pro' | 'con' | 'neutral'>('neutral');
  const [moderatorStyleId, setModeratorStyleId] = useState<string>('0');
  
  // 철학자 정보 모달 관련 상태
  const [selectedPhilosopherDetails, setSelectedPhilosopherDetails] = useState<Philosopher | null>(null);
  const [showPhilosopherDetails, setShowPhilosopherDetails] = useState(false);
  
  // 추천 주제 표시 상태
  const [showRecommendedTopics, setShowRecommendedTopics] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const moderatorStyles = [
    { id: '0', name: 'Jamie the Host', description: 'Casual and friendly young-style moderator' },
    { id: '1', name: 'Dr. Lee', description: 'Polite and academic university professor-style moderator' },
    { id: '2', name: 'Zuri Show', description: 'Energetic and entertaining YouTuber host-style moderator' },
    { id: '3', name: 'Elias of the End', description: 'Serious and weighty tone moderator' },
    { id: '4', name: 'Miss Hana', description: 'Bright and educational style moderator' }
  ];

  // Handle form field changes
  const handleChange = (field: keyof ChatRoomCreationParams, value: string | string[] | number | boolean) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Handle philosopher selection
  const togglePhilosopher = (philosopherName: string) => {
    setSelectedPhilosophers(prev => {
      const newSelection = prev.includes(philosopherName)
        ? prev.filter(p => p !== philosopherName)
        : [...prev, philosopherName];
      
      // Update formData.npcs
      const allSelected = [...newSelection, ...selectedCustomNpcs];
      handleChange('npcs', allSelected);
      
      return newSelection;
    });

    // Handle npcPositions for debate mode
    if (formData.dialogueType === 'debate') {
      if (selectedPhilosophers.includes(philosopherName)) {
        // Removing philosopher - remove position
        setNpcPositions(prev => {
          const updated = { ...prev };
          delete updated[philosopherName];
          return updated;
        });
      } else {
        // Adding philosopher - assign balanced position
        const proCount = Object.values(npcPositions).filter(p => p === 'pro').length;
        const conCount = Object.values(npcPositions).filter(p => p === 'con').length;
        const defaultPosition = proCount <= conCount ? 'pro' : 'con';
        
        setNpcPositions(prev => ({
          ...prev,
          [philosopherName]: defaultPosition
        }));
      }
    }
  };

  // Handle custom NPC selection
  const toggleCustomNpc = (npcName: string) => {
    setSelectedCustomNpcs(prev => {
      const newSelection = prev.includes(npcName)
        ? prev.filter(n => n !== npcName)
        : [...prev, npcName];
      
      // Update formData.npcs
      const allSelected = [...selectedPhilosophers, ...newSelection];
      handleChange('npcs', allSelected);
      
      return newSelection;
    });

    // Handle npcPositions for debate mode
    if (formData.dialogueType === 'debate') {
      if (selectedCustomNpcs.includes(npcName)) {
        // Removing NPC - remove position
        setNpcPositions(prev => {
          const updated = { ...prev };
          delete updated[npcName];
          return updated;
        });
      } else {
        // Adding NPC - assign balanced position
        const proCount = Object.values(npcPositions).filter(p => p === 'pro').length;
        const conCount = Object.values(npcPositions).filter(p => p === 'con').length;
        const defaultPosition = proCount <= conCount ? 'pro' : 'con';
        
        setNpcPositions(prev => ({
          ...prev,
          [npcName]: defaultPosition
        }));
      }
    }
  };

  // Handle file upload
  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        handleChange('contextFileContent', content);
        handleChange('context', `File: ${file.name}`);
      };
      reader.readAsText(file);
    }
  };

  // Handle dialogue type change
  const handleDialogueTypeChange = (type: string) => {
    handleChange('dialogueType', type as 'free' | 'debate' | 'socratic' | 'dialectical');
    if (type !== 'debate') {
      setNpcPositions({});
      setUserDebateRole('neutral');
    }
  };

  // Set NPC position for debate
  const setNpcPosition = (npcId: string, position: 'pro' | 'con') => {
    if (selectedPhilosophers.includes(npcId) || selectedCustomNpcs.includes(npcId)) {
      setNpcPositions(prev => ({
        ...prev,
        [npcId]: position
      }));
    }
  };

  // 철학자 정보 로드 함수
  const loadPhilosopherDetails = async (philosopherId: string) => {
    try {
      // 먼저 커스텀 NPC에서 찾기
      const customNpc = customNpcs.find(p => p.id.toLowerCase() === philosopherId.toLowerCase());
      if (customNpc) {
        setSelectedPhilosopherDetails(customNpc);
        setShowPhilosopherDetails(true);
        return;
      }
      
      // 이미 로드한 기본 철학자 정보가 있다면 재활용
      const existingPhil = philosophers.find(p => p.id.toLowerCase() === philosopherId.toLowerCase());
      if (existingPhil && existingPhil.description) {
        setSelectedPhilosopherDetails(existingPhil);
        setShowPhilosopherDetails(true);
        return;
      }
      
      // API 호출로 상세정보 가져오기
      const response = await fetch(`http://localhost:8000/api/philosophers/${philosopherId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedPhilosopherDetails(data);
        setShowPhilosopherDetails(true);
      } else {
        console.error(`Failed to fetch details for philosopher: ${philosopherId}`);
      }
    } catch (error) {
      console.error('Error fetching philosopher details:', error);
    }
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.title.trim()) {
      alert('Please enter a chat title');
      return;
    }

    // Prepare context based on type
    let finalContext = '';
    if (contextType === 'url' && formData.contextUrl) {
      finalContext = `URL: ${formData.contextUrl}`;
    } else if (contextType === 'file' && formData.contextFileContent) {
      finalContext = formData.contextFileContent;
    }

    const finalFormData: ChatRoomCreationParams = {
      ...formData,
      context: finalContext,
      contextUrl: contextType === 'url' ? formData.contextUrl : undefined,
      contextFileContent: contextType === 'file' ? formData.contextFileContent : undefined
    };

    // Add debate-specific data
    if (formData.dialogueType === 'debate') {
      finalFormData.npcPositions = npcPositions;
      finalFormData.userDebateRole = userDebateRole;
      finalFormData.moderator = {
        style_id: moderatorStyleId,
        style: moderatorStyles.find(s => s.id === moderatorStyleId)?.name || 'Jamie the Host'
      };
    }

    try {
      await onCreateChat(finalFormData);
    } catch (error) {
      console.error('Error creating chat:', error);
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      title: '',
      maxParticipants: 6,
      npcs: [],
      isPublic: true,
      generateInitialMessage: true,
      dialogueType: 'free',
      context: '',
      contextUrl: '',
      contextFileContent: ''
    });
    setContextType('none');
    setSelectedPhilosophers([]);
    setSelectedCustomNpcs([]);
    setNpcPositions({});
    setUserDebateRole('neutral');
    setModeratorStyleId('0');
    setStep(1);
    // 철학자 정보 모달 상태 초기화
    setSelectedPhilosopherDetails(null);
    setShowPhilosopherDetails(false);
    // 추천 주제 상태 초기화
    setShowRecommendedTopics(false);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const goToNextStep = () => {
    if (step < 3) {
      setStep((prev) => (prev + 1) as 1 | 2 | 3);
    }
  };

  const goToPreviousStep = () => {
    if (step > 1) {
      setStep((prev) => (prev - 1) as 1 | 2 | 3);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Background overlay */}
      <div className="create-chat-modal-overlay" onClick={handleClose}></div>
      
      {/* Modal container */}
      <div className="create-chat-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="create-chat-modal-header">
          <h2 className="text-2xl font-bold">Create New Chat</h2>
          <button 
            onClick={handleClose}
            className="create-chat-modal-close"
            disabled={isCreating}
          >
            ✕
          </button>
        </div>
        
        {/* Content */}
        <div className="create-chat-modal-content">
          <form onSubmit={handleSubmit}>
            {/* Step 1: Dialogue Pattern */}
            {step === 1 && (
              <div className="create-chat-step-container">
                <label className="create-chat-label">Dialogue Pattern</label>
                <div className="dialogue-pattern-grid">
                  <div 
                    className={`dialogue-pattern-card ${formData.dialogueType === 'free' ? 'selected' : ''}`}
                    onClick={() => handleDialogueTypeChange('free')}
                  >
                    <img src="/Free.png" alt="Free Discussion" className="dialogue-pattern-image" />
                    <div className="dialogue-pattern-title">Free Discussion</div>
                    <div className="dialogue-pattern-tooltip">
                      Open-format dialogue<br/>with no specific structure
                    </div>
                  </div>
                  
                  <div 
                    className={`dialogue-pattern-card ${formData.dialogueType === 'debate' ? 'selected' : ''}`}
                    onClick={() => handleDialogueTypeChange('debate')}
                  >
                    <img src="/ProCon.png" alt="Pro-Con Debate" className="dialogue-pattern-image" />
                    <div className="dialogue-pattern-title">Pro-Con Debate</div>
                    <div className="dialogue-pattern-tooltip">
                      Structured debate<br/>with opposing positions
                    </div>
                  </div>
                  
                  <div 
                    className={`dialogue-pattern-card ${formData.dialogueType === 'socratic' ? 'selected' : ''}`}
                    onClick={() => handleDialogueTypeChange('socratic')}
                  >
                    <img src="/Socratic.png" alt="Socratic Dialogue" className="dialogue-pattern-image" />
                    <div className="dialogue-pattern-title">Socratic Dialogue</div>
                    <div className="dialogue-pattern-tooltip">
                      Question-based approach<br/>to explore a topic
                    </div>
                  </div>
                  
                  <div 
                    className={`dialogue-pattern-card ${formData.dialogueType === 'dialectical' ? 'selected' : ''}`}
                    onClick={() => handleDialogueTypeChange('dialectical')}
                  >
                    <img src="/Dialectical.png" alt="Dialectical Discussion" className="dialogue-pattern-image" />
                    <div className="dialogue-pattern-title">Dialectical Discussion</div>
                    <div className="dialogue-pattern-tooltip">
                      Thesis-Antithesis-Synthesis<br/>format
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Chat Title and Context */}
            {step === 2 && (
              <div className="create-chat-step-container">
                <div className="mb-8">
                  <label className="create-chat-label">Chat Title:</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => handleChange('title', e.target.value)}
                    placeholder="What would you like to discuss today?"
                    className="create-chat-input"
                    required
                  />
                </div>

                {/* Recommended Topics Section */}
                <div className="recommended-topics-section">
                  <div 
                    className="recommended-topics-header"
                    onClick={() => setShowRecommendedTopics(!showRecommendedTopics)}
                  >
                    <div className="recommended-topics-label">
                      <svg 
                        className="recommended-topics-icon" 
                        xmlns="http://www.w3.org/2000/svg" 
                        viewBox="0 0 24 24" 
                        fill="none" 
                        stroke="currentColor" 
                        strokeWidth="2" 
                        strokeLinecap="round" 
                        strokeLinejoin="round"
                      >
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                      </svg>
                      Recommended Topics for {
                        formData.dialogueType === 'free' ? 'Free Discussion' :
                        formData.dialogueType === 'debate' ? 'Pro-Con Debate' :
                        formData.dialogueType === 'socratic' ? 'Socratic Dialogue' :
                        'Dialectical Discussion'
                      }
                    </div>
                  </div>
                  
                  <div className={`recommended-topics-content ${showRecommendedTopics ? '' : 'hidden'}`}>
                    {formData.dialogueType === 'free' && (
                      <ul className="recommended-topics-list">
                        <li>&quot;The meaning of happiness in different philosophical traditions&quot;</li>
                        <li>&quot;How does technology shape human experience in the modern world?&quot;</li>
                        <li>&quot;The relationship between art and moral values&quot;</li>
                        <li>&quot;Free will and determinism: Are our choices truly free?&quot;</li>
                        <li>&quot;The nature of consciousness and self-awareness&quot;</li>
                      </ul>
                    )}
                    
                    {formData.dialogueType === 'debate' && (
                      <ul className="recommended-topics-list">
                        <li>&quot;Is artificial intelligence beneficial or harmful to humanity?&quot;</li>
                        <li>&quot;Should we prioritize individual liberty over collective welfare?&quot;</li>
                        <li>&quot;Is objective morality possible without religion?&quot;</li>
                        <li>&quot;Should societies focus on equality of opportunity or equality of outcome?&quot;</li>
                        <li>&quot;Is human nature fundamentally good or self-interested?&quot;</li>
                      </ul>
                    )}
                    
                    {formData.dialogueType === 'socratic' && (
                      <ul className="recommended-topics-list">
                        <li>&quot;What is justice? How can we recognize a just society?&quot;</li>
                        <li>&quot;What constitutes knowledge versus mere opinion?&quot;</li>
                        <li>&quot;What is the nature of virtue? Can it be taught?&quot;</li>
                        <li>&quot;What makes a life worth living? How should we define success?&quot;</li>
                        <li>&quot;How should we understand the relationship between mind and body?&quot;</li>
                      </ul>
                    )}
                    
                    {formData.dialogueType === 'dialectical' && (
                      <ul className="recommended-topics-list">
                        <li>&quot;Thesis: Reason is the primary source of knowledge | Antithesis: Experience is the primary source of knowledge&quot;</li>
                        <li>&quot;Thesis: Morality is objective | Antithesis: Morality is culturally relative&quot;</li>
                        <li>&quot;Thesis: Human technology enhances our humanity | Antithesis: Technology alienates us from our true nature&quot;</li>
                        <li>&quot;Thesis: Free markets maximize human flourishing | Antithesis: Markets require regulation to prevent exploitation&quot;</li>
                        <li>&quot;Thesis: Mind is separate from matter | Antithesis: Mind emerges from physical processes&quot;</li>
                      </ul>
                    )}
                  </div>
                  
                  {/* Quick topic buttons */}
                  <div className="topic-quick-buttons">
                    {formData.dialogueType === 'free' && (
                      <>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "The meaning of happiness in different philosophical traditions")}
                          className="topic-quick-button"
                        >
                          Happiness
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "The nature of consciousness and self-awareness")}
                          className="topic-quick-button"
                        >
                          Consciousness
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "How does technology shape human experience?")}
                          className="topic-quick-button"
                        >
                          Technology & Humanity
                        </button>
                      </>
                    )}
                    
                    {formData.dialogueType === 'debate' && (
                      <>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "Is artificial intelligence beneficial or harmful to humanity?")}
                          className="topic-quick-button"
                        >
                          AI Ethics
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "Individual liberty vs. collective welfare")}
                          className="topic-quick-button"
                        >
                          Liberty vs. Community
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "Is human nature fundamentally good or self-interested?")}
                          className="topic-quick-button"
                        >
                          Human Nature
                        </button>
                      </>
                    )}
                    
                    {formData.dialogueType === 'socratic' && (
                      <>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "What is justice? How can we recognize a just society?")}
                          className="topic-quick-button"
                        >
                          On Justice
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "What constitutes knowledge versus mere opinion?")}
                          className="topic-quick-button"
                        >
                          Knowledge vs. Opinion
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "What makes a life worth living?")}
                          className="topic-quick-button"
                        >
                          The Good Life
                        </button>
                      </>
                    )}
                    
                    {formData.dialogueType === 'dialectical' && (
                      <>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "Reason vs. Experience as the source of knowledge")}
                          className="topic-quick-button"
                        >
                          Reason vs. Experience
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "Is morality objective or culturally relative?")}
                          className="topic-quick-button"
                        >
                          Moral Objectivity
                        </button>
                        <button 
                          type="button" 
                          onClick={() => handleChange('title', "Mind-body relationship: dualism or physicalism?")}
                          className="topic-quick-button"
                        >
                          Mind-Body Problem
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <div className="mb-6">
                  <label className="create-chat-label">Context</label>
                  
                  {/* Context type selection */}
                  <div className="flex border-b border-gray-200 mb-4">
                    <button
                      type="button"
                      onClick={() => setContextType('none')}
                      className={`px-4 py-2 font-medium ${
                        contextType === 'none'
                          ? 'border-b-2 border-black text-black'
                          : 'text-gray-500 hover:text-black'
                      }`}
                    >
                      None
                    </button>
                    <button
                      type="button"
                      onClick={() => setContextType('url')}
                      className={`px-4 py-2 font-medium ${
                        contextType === 'url'
                          ? 'border-b-2 border-black text-black'
                          : 'text-gray-500 hover:text-black'
                      }`}
                    >
                      URL
                    </button>
                    <button
                      type="button"
                      onClick={() => setContextType('file')}
                      className={`px-4 py-2 font-medium ${
                        contextType === 'file'
                          ? 'border-b-2 border-black text-black'
                          : 'text-gray-500 hover:text-black'
                      }`}
                    >
                      File
                    </button>
                  </div>

                  {/* URL input */}
                  {contextType === 'url' && (
                    <input
                      type="url"
                      value={formData.contextUrl}
                      onChange={(e) => handleChange('contextUrl', e.target.value)}
                      placeholder="https://example.com/article"
                      className="create-chat-input"
                    />
                  )}

                  {/* File upload */}
                  {contextType === 'file' && (
                    <div>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".txt,.md,.pdf"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                      >
                        <DocumentArrowUpIcon className="h-5 w-5" />
                        {formData.context || 'Choose file (txt, md, pdf)'}
                      </button>
                    </div>
                  )}
                </div>

                <div className="mb-6">
                  <label className="create-chat-label">Maximum Participants:</label>
                  <input
                    type="number"
                    value={formData.maxParticipants}
                    onChange={(e) => handleChange('maxParticipants', parseInt(e.target.value))}
                    min="2"
                    max="10"
                    className="create-chat-input"
                  />
                </div>

                <div className="mb-6">
                  <label className="block mb-3 font-medium text-lg">Chat Visibility</label>
                  <div className="flex gap-6">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="visibility"
                        checked={formData.isPublic}
                        onChange={() => handleChange('isPublic', true)}
                        className="mr-2 h-5 w-5"
                      />
                      <span className="text-lg">Public (anyone can join)</span>
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="visibility"
                        checked={!formData.isPublic}
                        onChange={() => handleChange('isPublic', false)}
                        className="mr-2 h-5 w-5"
                      />
                      <span className="text-lg">Private (invite only)</span>
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Participants */}
            {step === 3 && (
              <div className="create-chat-step-container">
                <label className="block mb-4 font-medium text-lg">Select Participants</label>
                
                {/* User debate role for debate type */}
                {formData.dialogueType === 'debate' && (
                  <div className="debate-role-selection-container">
                    <h3 className="debate-role-selection-title">Select Your Role in the Debate</h3>
                    <div className="debate-role-cards-container">
                      <div 
                        onClick={() => setUserDebateRole('pro')}
                        className={`debate-role-card ${userDebateRole === 'pro' ? 'pro' : ''}`}
                      >
                        <div className="debate-role-card-title">
                          Pro (Affirmative)
                        </div>
                        <div className="debate-role-card-description">Support the proposition</div>
                      </div>
                      
                      <div 
                        onClick={() => setUserDebateRole('con')}
                        className={`debate-role-card ${userDebateRole === 'con' ? 'con' : ''}`}
                      >
                        <div className="debate-role-card-title">
                          Con (Negative)
                        </div>
                        <div className="debate-role-card-description">Oppose the proposition</div>
                      </div>
                      
                      <div 
                        onClick={() => setUserDebateRole('neutral')}
                        className={`debate-role-card ${userDebateRole === 'neutral' ? 'neutral' : ''}`}
                      >
                        <div className="debate-role-card-title">
                          Observer
                        </div>
                        <div className="debate-role-card-description">Watch the debate neutrally</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Moderator styles for debate */}
                {formData.dialogueType === 'debate' && (
                  <div className="mb-6">
                    <h3 className="text-base font-medium mb-3">Select Moderator Style</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {moderatorStyles.map(style => (
                        <div 
                          key={style.id}
                          onClick={() => setModeratorStyleId(style.id)}
                          className={`moderator-selection-card ${
                            moderatorStyleId === style.id ? 'selected' : ''
                          }`}
                        >
                          <div className="moderator-card-content">
                            <img
                              src={`/portraits/Moderator${style.id}.png`}
                              alt={style.name}
                              className="moderator-image"
                            />
                            <div className="moderator-info">
                              <div className="moderator-name">{style.name}</div>
                              <div className="moderator-description">{style.description}</div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Selected philosophers display */}
                {(selectedPhilosophers.length > 0 || selectedCustomNpcs.length > 0) && (
                  <div className="mb-6">
                    <h3 className="text-base font-medium mb-3">
                      Selected Philosophers ({selectedPhilosophers.length + selectedCustomNpcs.length})
                    </h3>
                    <div className="flex flex-wrap gap-4">
                      {[...selectedPhilosophers, ...selectedCustomNpcs].map(npcId => {
                        const npc = [...philosophers, ...customNpcs].find(p => p.id === npcId || p.name === npcId);
                        if (!npc) return null;
                        
                        return (
                          <div key={npcId} className="selected-philosopher-container">
                            <div className="selected-philosopher-image-wrapper">
                              <img
                                src={npc.portrait_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(npc.name)}&background=random&size=64`}
                                alt={npc.name}
                                className="philosopher-image-medium"
                              />
                              <button
                                onClick={() => {
                                  if (selectedPhilosophers.includes(npcId)) {
                                    togglePhilosopher(npcId);
                                  } else {
                                    toggleCustomNpc(npcId);
                                  }
                                }}
                                className="selected-philosopher-remove"
                                aria-label="Remove philosopher"
                              >
                                ×
                              </button>
                              
                              {/* Debate positions */}
                              {formData.dialogueType === 'debate' && (
                                <div className="debate-position-buttons">
                                  <button
                                    type="button"
                                    onClick={() => setNpcPosition(npcId, 'pro')}
                                    className={`debate-position-button ${
                                      npcPositions[npcId] === 'pro' ? 'pro' : 'neutral'
                                    }`}
                                  >
                                    Pro
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setNpcPosition(npcId, 'con')}
                                    className={`debate-position-button ${
                                      npcPositions[npcId] === 'con' ? 'con' : 'neutral'
                                    }`}
                                  >
                                    Con
                                  </button>
                                </div>
                              )}
                            </div>
                            <span className="selected-philosopher-name">
                              {npc.name}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Custom NPCs */}
                {customNpcs.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-base font-medium mb-2">My Custom Philosophers</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {customNpcs.map(npc => (
                        <div 
                          key={npc.id}
                          className={`philosopher-selection-card ${
                            selectedCustomNpcs.includes(npc.id) ? 'selected' : ''
                          }`}
                        >
                          <div 
                            className="philosopher-card-content"
                            onClick={() => toggleCustomNpc(npc.id)}
                          >
                            <img
                              src={npc.portrait_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(npc.name)}&background=random&size=32`}
                              alt={npc.name}
                              className="philosopher-image-small"
                            />
                            <span className="philosopher-card-name">{npc.name}</span>
                          </div>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              loadPhilosopherDetails(npc.id);
                              return false;
                            }}
                            className="view-details-button"
                          >
                            View details
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Classic Philosophers */}
                <div>
                  <h3 className="text-base font-medium mb-2">Classic Philosophers</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {philosophers.map(philosopher => (
                      <div 
                        key={philosopher.id}
                        className={`philosopher-selection-card ${
                          selectedPhilosophers.includes(philosopher.id) ? 'selected' : ''
                        }`}
                      >
                        <div 
                          className="philosopher-card-content"
                          onClick={() => togglePhilosopher(philosopher.id)}
                        >
                          <img
                            src={philosopher.portrait_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(philosopher.name)}&background=random&size=32`}
                            alt={philosopher.name}
                            className="philosopher-image-small"
                          />
                          <span className="philosopher-card-name">{philosopher.name}</span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            loadPhilosopherDetails(philosopher.id);
                            return false;
                          }}
                          className="view-details-button"
                        >
                          View details
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </form>
        </div>

        {/* Footer Navigation */}
        <div className="create-chat-footer">
          <div className="create-chat-navigation">
            <button
              type="button"
              onClick={goToPreviousStep}
              className="create-chat-nav-button"
              disabled={step <= 1}
              style={{ visibility: step > 1 ? 'visible' : 'hidden' }}
            >
              &lt;
            </button>
            
            <div className="create-chat-step-indicator">
              {step}/3
            </div>
            
            <button
              type="button"
              onClick={goToNextStep}
              className="create-chat-nav-button"
              disabled={step >= 3 || (step === 1 && !formData.dialogueType)}
              style={{ visibility: step < 3 ? 'visible' : 'hidden' }}
            >
              &gt;
            </button>
          </div>
        </div>

        {/* Submit Button */}
        {step === 3 && (
          <div className="create-chat-actions">
            <button
              type="button"
              onClick={handleSubmit}
              className="create-chat-submit"
              disabled={!formData.title.trim() || (selectedPhilosophers.length + selectedCustomNpcs.length) === 0 || isCreating}
            >
              {isCreating ? (
                <>
                  <span className="loading-spinner"></span>
                  Creating...
                </>
              ) : (
                'Create Chat'
              )}
            </button>
          </div>
        )}
      </div>
      
      {/* Philosopher Details Modal */}
      <PhilosopherDetailsModal
        philosopher={selectedPhilosopherDetails}
        isOpen={showPhilosopherDetails}
        onClose={() => setShowPhilosopherDetails(false)}
        onToggleSelect={(philosopherId) => {
          // 선택된 철학자 목록에서 찾기
          if (selectedPhilosophers.includes(philosopherId)) {
            togglePhilosopher(philosopherId);
          } else if (selectedCustomNpcs.includes(philosopherId)) {
            toggleCustomNpc(philosopherId);
          } else {
            // 아직 선택되지 않은 경우 적절한 목록에 추가
            const isCustomNpc = customNpcs.some(npc => npc.id === philosopherId);
            if (isCustomNpc) {
              toggleCustomNpc(philosopherId);
            } else {
              togglePhilosopher(philosopherId);
            }
          }
        }}
        isSelected={selectedPhilosophers.includes(selectedPhilosopherDetails?.id || '') || 
                   selectedCustomNpcs.includes(selectedPhilosopherDetails?.id || '')}
      />
    </>
  );
};

export default CreateChatModal; 