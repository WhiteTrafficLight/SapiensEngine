'use client';

import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const Modal: React.FC<ModalProps> = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  footer 
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    if (isOpen) {
      document.body.classList.add('modal-open');
    } else {
      document.body.classList.remove('modal-open');
    }
    
    return () => {
      document.body.classList.remove('modal-open');
    };
  }, [isOpen]);

  // Handle escape key press
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (isOpen) {
      window.addEventListener('keydown', handleEsc);
    }
    
    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, [isOpen, onClose]);

  // Don't render on the server
  if (!mounted || !isOpen) return null;
  
  // Create portal for modal
  return createPortal(
    <div className="modal-wrapper">
      {/* Backdrop */}
      <div 
        className="modal-backdrop fixed inset-0 bg-black bg-opacity-80 backdrop-blur-md"
        onClick={onClose}
        style={{ zIndex: 9998 }}
      ></div>
      
      {/* Modal */}
      <div 
        className="modal-container fixed w-[95%] sm:w-[90%] md:w-[85%] max-w-[900px] max-h-[90vh] bg-white rounded-3xl overflow-hidden"
        style={{ 
          zIndex: 9999,
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="modal-header px-8 py-6 border-b border-gray-200 flex justify-between items-center bg-gray-50 rounded-t-3xl">
          <h2 className="text-2xl font-bold">{title}</h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-black transition-colors p-2 rounded-full hover:bg-gray-200"
          >
            <XMarkIcon className="h-8 w-8" />
          </button>
        </div>
        
        {/* Modal content */}
        <div className="modal-content p-8 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 160px)' }}>
          {children}
        </div>
        
        {/* Modal footer */}
        {footer && (
          <div className="modal-footer px-8 py-6 border-t border-gray-200 bg-gray-50">
            {footer}
          </div>
        )}
      </div>
      
      <style jsx global>{`
        body.modal-open {
          overflow: hidden;
          position: fixed;
          width: 100%;
          height: 100%;
        }
        
        .modal-wrapper {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          isolation: isolate;
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes slideIn {
          from { 
            opacity: 0;
            transform: translate(-50%, -48%) scale(0.92);
          }
          to { 
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
        }
        
        .modal-backdrop {
          animation: fadeIn 0.3s ease-out;
        }
        
        .modal-container {
          animation: slideIn 0.4s ease-out;
        }
      `}</style>
    </div>,
    document.body
  );
};

export default Modal; 