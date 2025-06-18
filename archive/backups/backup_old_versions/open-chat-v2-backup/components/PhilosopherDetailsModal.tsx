import React from 'react';

interface Philosopher {
  id: string;
  name: string;
  period?: string; 
  nationality?: string;
  description?: string;
  key_concepts?: string[];
  portrait_url?: string;
}

interface PhilosopherDetailsModalProps {
  philosopher: Philosopher | null;
  isOpen: boolean;
  onClose: () => void;
  onToggleSelect: (philosopherId: string) => void;
  isSelected: boolean;
}

const PhilosopherDetailsModal: React.FC<PhilosopherDetailsModalProps> = ({
  philosopher,
  isOpen,
  onClose,
  onToggleSelect,
  isSelected
}) => {
  if (!isOpen || !philosopher) {
    return null;
  }

  // 기본 아바타 생성 함수
  const getDefaultAvatar = () => {
    const name = philosopher.name || 'Philosopher';
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random&size=128&font-size=0.5`;
  };

  const handleToggleSelect = () => {
    onToggleSelect(philosopher.id);
    onClose();
  };

  return (
    <>
      {/* Background overlay */}
      <div 
        className="philosopher-details-modal-overlay"
        onClick={onClose}
      >
        {/* Modal container */}
        <div 
          className="philosopher-details-modal-container"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button 
            className="philosopher-details-close"
            onClick={onClose}
          >
            ✕
          </button>
          
          {/* Header with avatar and basic info */}
          <div className="philosopher-details-header">
            <div className="philosopher-details-avatar">
              <img
                src={philosopher.portrait_url || getDefaultAvatar()}
                alt={philosopher.name}
                onError={(e) => {
                  // 이미지 로드 실패 시 기본 아바타로 대체
                  (e.target as HTMLImageElement).src = getDefaultAvatar();
                }}
              />
            </div>
            <div className="philosopher-details-info">
              <h3>{philosopher.name}</h3>
              {philosopher.period && (
                <div className="philosopher-details-meta">
                  {philosopher.nationality && `${philosopher.nationality} • `}
                  {philosopher.period}
                </div>
              )}
            </div>
          </div>
          
          {/* Description */}
          {philosopher.description && (
            <div className="philosopher-details-description">
              {philosopher.description}
            </div>
          )}
          
          {/* Key concepts */}
          {philosopher.key_concepts && philosopher.key_concepts.length > 0 && (
            <div className="philosopher-details-concepts">
              <h4>Key Concepts</h4>
              <div className="philosopher-concepts-list">
                {philosopher.key_concepts.map((concept, index) => (
                  <span key={index} className="philosopher-concept-tag">
                    {concept}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Actions */}
          <div className="philosopher-details-actions">
            <button 
              className="philosopher-details-action-button"
              onClick={handleToggleSelect}
            >
              {isSelected ? 'Remove from Chat' : 'Add to Chat'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default PhilosopherDetailsModal; 