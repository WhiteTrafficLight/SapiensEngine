import React from 'react';
import { SocketStatus } from '../types/openChat.types';

interface SocketStatusIndicatorProps extends SocketStatus {
  className?: string;
}

const SocketStatusIndicator: React.FC<SocketStatusIndicatorProps> = ({
  connected,
  onReconnect,
  className = ''
}) => {
  if (connected) {
    return null;
  }

  return (
    <div className={`fixed top-0 left-0 right-0 bg-red-500 text-white p-2 text-center text-sm z-50 ${className}`}>
      Socket disconnected. Real-time updates may not work.
      <button 
        onClick={onReconnect} 
        className="ml-2 px-2 py-0.5 bg-white text-red-500 rounded text-xs font-bold hover:bg-gray-100"
      >
        Reconnect
      </button>
    </div>
  );
};

export default SocketStatusIndicator;