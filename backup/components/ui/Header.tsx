import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const Header = () => {
  const pathname = usePathname();

  const isActive = (path: string) => {
    return pathname === path;
  };

  return (
    <header className="bg-white border-b-2 border-black">
      <div className="container mx-auto px-4 flex items-center h-16 max-w-6xl">
        <div className="w-1/6">
          {/* Logo 부분 제거 */}
        </div>
        
        <div className="w-4/6 flex items-center justify-between">
          <Link 
            href="/" 
            className={`nav-item text-2xl font-bold text-black ${isActive('/') ? 'active-nav' : 'hover-blur'}`}
          >
            Home
          </Link>
          <Link 
            href="/open-chat" 
            className={`nav-item text-2xl font-bold text-black ${isActive('/open-chat') ? 'active-nav' : 'hover-blur'}`}
          >
            Open Chat
          </Link>
          <Link 
            href="/settings" 
            className={`nav-item text-2xl font-bold text-black ${isActive('/settings') ? 'active-nav' : 'hover-blur'}`}
          >
            Settings
          </Link>
        </div>
        
        <div className="w-1/6 flex justify-end">
          <Link href="/settings" className="text-black hover:text-gray-600 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </Link>
        </div>
      </div>
    </header>
  );
};

export default Header; 