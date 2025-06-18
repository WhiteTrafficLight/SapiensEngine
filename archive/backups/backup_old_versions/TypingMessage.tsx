import React, { useEffect, useRef } from 'react';
import { useTypingAnimation } from '@/hooks/useTypingAnimation';

interface TypingMessageProps {
  text: string;
  speed?: number;
  delay?: number;
  enabled?: boolean;
  showCursor?: boolean;
  autoStart?: boolean;
  onTypingComplete?: () => void;
  className?: string;
  style?: React.CSSProperties;
}

const TypingMessage: React.FC<TypingMessageProps> = ({
  text,
  speed = 20,
  delay = 0,
  enabled = true,
  showCursor = true,
  autoStart = true,
  onTypingComplete,
  className = '',
  style = {}
}) => {
  const { displayedText, isTyping, startTyping } = useTypingAnimation({
    text,
    speed,
    delay,
    enabled
  });
  
  const prevTypingRef = useRef(isTyping);

  // 자동 시작
  useEffect(() => {
    if (autoStart && enabled && text) {
      startTyping();
    }
  }, [autoStart, enabled, text, startTyping]);

  // 타이핑 완료 콜백
  useEffect(() => {
    if (prevTypingRef.current && !isTyping && onTypingComplete) {
      onTypingComplete();
    }
    prevTypingRef.current = isTyping;
  }, [isTyping, onTypingComplete]);

  return (
    <span className={className} style={style}>
      {displayedText}
      {showCursor && isTyping && (
        <span 
          style={{
            display: 'inline-block',
            width: '2px',
            height: '1.2em',
            backgroundColor: 'currentColor',
            marginLeft: '2px',
            animation: 'blink 1s infinite'
          }}
        />
      )}
      
      {/* CSS 애니메이션 정의 */}
      <style jsx>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </span>
  );
};

export default TypingMessage; 