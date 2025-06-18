import React from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/outline';

interface MessageInputProps {
  messageText: string;
  setMessageText: (text: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isUserTurn: boolean;
  isInputDisabled: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  isGeneratingResponse: boolean;
  currentUserTurn?: {speaker_id: string, role: string} | null;
  waitingForUserInput?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({
  messageText,
  setMessageText,
  onSubmit,
  isUserTurn,
  isInputDisabled,
  inputRef,
  isGeneratingResponse,
  currentUserTurn,
  waitingForUserInput
}) => {
  
  // Enter 키 처리
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isInputDisabled) {
      e.preventDefault();
      onSubmit(e as unknown as React.FormEvent);
    }
  };

  // 플레이스홀더 텍스트 생성
  const getPlaceholderText = () => {
    if (waitingForUserInput && currentUserTurn) {
      const roleText = currentUserTurn.role === 'pro' ? 'Pro' : 
                      currentUserTurn.role === 'con' ? 'Con' : 
                      currentUserTurn.role;
      return `It's your turn (${roleText} side). Please enter your opinion.`;
    } else if (isUserTurn) {
      return "It's your turn now. Please enter your message.";
    } else {
      return "Press the Next button to continue the conversation.";
    }
  };

  // 턴 메시지 생성
  const getTurnMessage = () => {
    if (waitingForUserInput && currentUserTurn) {
      const roleText = currentUserTurn.role === 'pro' ? 'Pro' : 
                      currentUserTurn.role === 'con' ? 'Con' : 
                      currentUserTurn.role;
      return `It's your turn to speak as the ${roleText} side. Please enter your opinion.`;
    } else if (!isUserTurn && !isGeneratingResponse) {
      return "It's currently another participant's turn. You'll be notified when it's your turn.";
    }
    return null;
  };

  return (
    <div className={`debate-input-container ${isUserTurn ? 'user-turn' : ''}`}>
      <form onSubmit={onSubmit} className="debate-input-form">
        <textarea
          ref={inputRef}
          value={messageText}
          onChange={(e) => setMessageText(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={getPlaceholderText()}
          className={`debate-input-field ${
            isUserTurn ? 'user-turn' : 'disabled'
          }`}
          disabled={isInputDisabled}
        />
        
        <button
          type="submit"
          disabled={!messageText.trim() || isInputDisabled}
          className={`debate-send-button ${
            isUserTurn && messageText.trim() ? 'user-turn' : ''
          }`}
        >
          <PaperAirplaneIcon style={{ height: '20px', width: '20px' }} />
        </button>
      </form>
      
      {getTurnMessage() && (
        <div className="debate-turn-message">
          {getTurnMessage()}
        </div>
      )}
    </div>
  );
};

export default MessageInput; 