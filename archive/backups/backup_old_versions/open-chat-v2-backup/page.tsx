'use client';

import React from 'react';
import { Toaster } from 'react-hot-toast';
import OpenChatContainer from './components/OpenChatContainer';

export default function OpenChatPageV2() {
  return (
    <>
      {/* 메인 컨테이너 */}
      <OpenChatContainer />
      
      {/* Toast 알림 */}
      <Toaster position="top-right" />
    </>
  );
} 