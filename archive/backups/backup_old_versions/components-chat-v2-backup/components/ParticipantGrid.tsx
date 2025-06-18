import React from 'react';

interface ParticipantGridProps {
  proParticipants: string[];
  neutralParticipants: string[];
  conParticipants: string[];
  moderatorInfo: {
    name: string;
    profileImage: string;
  };
  selectedNpcId: string | null;
  isUserTurn: boolean;
  getNameFromId: (id: string, isUser: boolean) => string;
  getProfileImage: (id: string, isUser: boolean) => string;
  isUserParticipant: (id: string) => boolean;
}

const ParticipantGrid: React.FC<ParticipantGridProps> = ({
  proParticipants,
  neutralParticipants,
  conParticipants,
  moderatorInfo,
  selectedNpcId,
  isUserTurn,
  getNameFromId,
  getProfileImage,
  isUserParticipant
}) => {
  return (
    <div className="debate-participants-grid">
      {/* Pro Side */}
      <div className="debate-participants-column pro">
        {proParticipants.map(id => {
          const isUser = isUserParticipant(id);
          const name = getNameFromId(id, isUser);
          const avatar = getProfileImage(id, isUser);
          
          return (
            <div key={`pro-${id}`} className="debate-participant-card">
              <div className={`debate-participant-avatar pro ${
                selectedNpcId === id ? 'selected' : ''
              } ${isUserTurn && isUser ? 'user-turn' : ''}`}>
                <img src={avatar} alt={name} className="debate-participant-image" />
              </div>
              <div className="debate-participant-name">{name}</div>
              <div className="debate-participant-role pro">PRO</div>
            </div>
          );
        })}
      </div>
      
      {/* Neutral */}
      <div className="debate-participants-column neutral">
        {neutralParticipants.map(id => {
          const isUser = isUserParticipant(id);
          const name = getNameFromId(id, isUser);
          const avatar = getProfileImage(id, isUser);
          
          return (
            <div key={`neutral-${id}`} className="debate-participant-card">
              <div className={`debate-participant-avatar neutral ${
                selectedNpcId === id ? 'selected' : ''
              } ${isUserTurn && isUser ? 'user-turn' : ''}`}>
                <img src={avatar} alt={name} className="debate-participant-image" />
              </div>
              <div className="debate-participant-name">{name}</div>
              <div className="debate-participant-role neutral">NEUTRAL</div>
            </div>
          );
        })}
        
        {/* 모더레이터 */}
        <div key="moderator" className="debate-participant-card">
          <div className="debate-participant-avatar moderator">
            <img
              src={moderatorInfo.profileImage}
              alt={moderatorInfo.name}
              className="debate-participant-image"
            />
          </div>
          <div className="debate-participant-name">{moderatorInfo.name}</div>
          <div className="debate-participant-role moderator">MODERATOR</div>
        </div>
      </div>
      
      {/* Con Side */}
      <div className="debate-participants-column con">
        {conParticipants.map(id => {
          const isUser = isUserParticipant(id);
          const name = getNameFromId(id, isUser);
          const avatar = getProfileImage(id, isUser);
          
          return (
            <div key={`con-${id}`} className="debate-participant-card">
              <div className={`debate-participant-avatar con ${
                selectedNpcId === id ? 'selected' : ''
              } ${isUserTurn && isUser ? 'user-turn' : ''}`}>
                <img src={avatar} alt={name} className="debate-participant-image" />
              </div>
              <div className="debate-participant-name">{name}</div>
              <div className="debate-participant-role con">CON</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ParticipantGrid; 