import React from 'react';
import { ArrowDownCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import TypingMessage from '../../TypingMessage';

interface MessageListProps {
  messages: any[];
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  isUserTurn: boolean;
  typingMessageIds: Set<string>;
  getNameFromId: (id: string, isUser: boolean) => string;
  getProfileImage: (id: string, isUser: boolean) => string;
  isUserParticipant: (id: string) => boolean;
  handleTypingComplete: (messageId: string) => void;
  showNextButton: boolean;
  onRequestNext: () => void;
  isGeneratingNext: boolean;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  messagesEndRef,
  isUserTurn,
  typingMessageIds,
  getNameFromId,
  getProfileImage,
  isUserParticipant,
  handleTypingComplete,
  showNextButton,
  onRequestNext,
  isGeneratingNext
}) => {
  const renderRagTooltip = (message: any) => {
    // 디버깅을 위한 콘솔 로그 추가
    console.log('🔍 RAG 정보 확인:', {
      messageId: message.id,
      rag_used: message.rag_used,
      rag_source_count: message.rag_source_count,
      rag_sources: message.rag_sources,
      hasRagSources: message.rag_sources && message.rag_sources.length > 0
    });

    if (!message.rag_used || !message.rag_sources || message.rag_sources.length === 0) {
      return null;
    }

    // 웹 소스 클릭 핸들러
    const handleSourceClick = (source: any) => {
      console.log('🔗 Source clicked:', source);
      console.log('🔗 Source type:', source.type);
      console.log('🔗 Source data:', source);
      
      if (source.type === 'web') {
        // 백엔드에서 사용하는 다양한 URL 필드명 확인
        let url = source.url || source.link || source.href || source.source;
        console.log('🔗 Found URL:', url);
        
        if (url) {
          // URL이 http/https로 시작하지 않으면 추가
          if (!url.startsWith('http://') && !url.startsWith('https://')) {
            if (url.startsWith('www.')) {
              url = 'https://' + url;
            } else if (url.includes('.')) {
              url = 'https://' + url;
            }
          }
          
          console.log('🔗 Final URL to open:', url);
          
          try {
            window.open(url, '_blank', 'noopener,noreferrer');
            console.log('✅ URL opened successfully');
          } catch (error) {
            console.error('❌ Error opening URL:', error);
            alert('Could not open the link. URL: ' + url);
          }
        } else {
          console.warn('⚠️ No URL found in web source');
          console.log('🔍 Available fields:', Object.keys(source));
          alert('No valid URL found for this source');
        }
      } else {
        console.log('🔗 Not a web source, no action taken');
      }
    };

    // 소스가 클릭 가능한지 확인
    const isClickable = (source: any) => {
      if (source.type !== 'web') return false;
      
      // 백엔드에서 사용하는 다양한 URL 필드명 확인
      const url = source.url || source.link || source.href || source.source;
      const hasValidUrl = url && (
        url.startsWith('http://') || 
        url.startsWith('https://') || 
        url.startsWith('www.') ||
        (typeof url === 'string' && url.includes('.'))
      );
      
      console.log('🔗 Checking if clickable:', { 
        type: source.type, 
        url, 
        hasValidUrl,
        availableFields: Object.keys(source)
      });
      
      return hasValidUrl;
    };

    return (
      <div className="debate-rag-indicator">
        <div className="debate-rag-icon" title={`RAG 검색 결과 ${message.rag_source_count}개 활용`}>
          <InformationCircleIcon style={{ height: '16px', width: '16px' }} />
          <span className="debate-rag-count">{message.rag_source_count}</span>
        </div>
        <div className="debate-rag-tooltip">
          <div className="debate-rag-tooltip-header">
            Sources ({message.rag_source_count})
          </div>
          <div className="debate-rag-tooltip-content">
            {message.rag_sources.slice(0, 3).map((source: any, idx: number) => (
              <div 
                key={idx} 
                className={`debate-rag-source-item ${isClickable(source) ? 'clickable' : ''}`}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleSourceClick(source);
                }}
                onMouseDown={(e) => {
                  // 마우스 다운 시에도 이벤트 전파 방지
                  e.preventDefault();
                  e.stopPropagation();
                }}
                title={isClickable(source) ? 'Click to open source' : ''}
                style={{ 
                  userSelect: 'none',
                  ...(isClickable(source) && { cursor: 'pointer' })
                }}
              >
                <div className="debate-rag-source-type">
                  {source.type === 'web' ? '🌐 Web' : 
                   source.type === 'context' ? '📄 Context' :
                   source.type === 'dialogue' ? '💬 Dialogue' :
                   source.type === 'philosopher' ? '🧠 Philosopher' : '📚 Source'}
                </div>
                <div className="debate-rag-source-content">
                  {source.content.substring(0, 100)}...
                </div>
                {source.relevance_score && (
                  <div className="debate-rag-source-score">
                    Relevance: {(source.relevance_score * 100).toFixed(1)}%
                  </div>
                )}
                {!source.relevance_score && source.relevance && (
                  <div className="debate-rag-source-score">
                    Relevance: {(source.relevance * 100).toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
            {message.rag_sources.length > 3 && (
              <div className="debate-rag-more">
                +{message.rag_sources.length - 3} more
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderMessage = (message: any, index: number) => {
    const isUser = isUserParticipant(message.sender);
    const senderName = getNameFromId(message.sender, isUser);
    const avatar = getProfileImage(message.sender, isUser);
    const isCurrentUserTurn = isUserTurn && isUser;
    const isTempWaitingMessage = message.id.startsWith('temp-waiting-');
    const isGeneratingMessage = message.isGenerating === true;
    
    return (
      <div 
        key={message.id} 
        className={`debate-message ${isCurrentUserTurn ? 'user-turn' : ''}`}
        style={{ animationDelay: `${index * 0.1}s` }}
      >
        <div className="debate-message-content">
          <div className="debate-message-avatar">
            <img src={avatar} alt={senderName} />
          </div>
          
          <div className="debate-message-body">
            <div className={`debate-message-sender ${message.role === 'moderator' ? 'moderator' : ''}`}>
              {senderName}
              {message.role === 'moderator' && (
                <span className="debate-moderator-badge">MODERATOR</span>
              )}
              {renderRagTooltip(message)}
            </div>
            
            <div className={`debate-message-text ${
              message.role === 'moderator' ? 'moderator' :
              isUser ? 'user' : 'system'
            } ${isTempWaitingMessage ? 'temp-waiting' : ''} ${isGeneratingMessage ? 'generating' : ''}`}>
              {isTempWaitingMessage ? (
                <div className="debate-message-waiting-dots">
                  <div className="debate-waiting-dots">
                    <div className="debate-waiting-dot" />
                    <div className="debate-waiting-dot" />
                    <div className="debate-waiting-dot" />
                  </div>
                  {message.text}
                </div>
              ) : isGeneratingMessage ? (
                <div className="debate-message-generating">
                  <div className="debate-generating-dots">
                    <div className="debate-generating-dot" />
                    <div className="debate-generating-dot" />
                    <div className="debate-generating-dot" />
                    <div className="debate-generating-dot" />
                    <div className="debate-generating-dot" />
                  </div>
                  <span className="debate-generating-text">thinking</span>
                </div>
              ) : (
                <div>
                  {typingMessageIds.has(message.id) ? (
                    <TypingMessage
                      text={message.text}
                      speed={30}
                      delay={200}
                      enabled={true}
                      showCursor={true}
                      autoStart={true}
                      onTypingComplete={() => handleTypingComplete(message.id)}
                    />
                  ) : (
                    message.text
                  )}
                </div>
              )}
              
              {message.citations && message.citations.length > 0 && (
                <div className="debate-message-citations">
                  <strong>출처:</strong>
                  <ul>
                    {message.citations.map((citation: any, idx: number) => (
                      <li key={idx}>
                        [{citation.id}] {citation.source}
                        {citation.location && ` (${citation.location})`}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            <div className="debate-message-timestamp">
              {new Date(message.timestamp).toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="debate-messages-container">
      {messages && messages.length > 0 ? (
        messages.map((message, index) => renderMessage(message, index))
      ) : (
        <div className="debate-no-messages">
          토론이 곧 시작됩니다...
        </div>
      )}
      
      {showNextButton && (
        <div className="debate-next-button-container">
          <button
            type="button"
            onClick={onRequestNext}
            disabled={isGeneratingNext}
            className="debate-next-button"
          >
            {isGeneratingNext ? (
              <>
                <div className="loading-spinner" />
                생성중...
              </>
            ) : (
              <>
                <ArrowDownCircleIcon style={{ height: '18px', width: '18px' }} />
                Next
              </>
            )}
          </button>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList; 