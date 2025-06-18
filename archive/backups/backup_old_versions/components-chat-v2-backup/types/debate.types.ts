// 토론 채팅 시스템의 핵심 타입 정의

export enum DebateStage {
  OPENING = 'opening',
  PRO_ARGUMENT = 'pro_argument',
  CON_ARGUMENT = 'con_argument',
  MODERATOR_SUMMARY_1 = 'moderator_summary_1',
  INTERACTIVE_ARGUMENT = 'interactive_argument',
  MODERATOR_SUMMARY_2 = 'moderator_summary_2',
  PRO_CONCLUSION = 'pro_conclusion',
  CON_CONCLUSION = 'con_conclusion',
  CLOSING = 'closing',
  COMPLETED = 'completed'
}

export enum ParticipantRole {
  PRO = 'pro',
  CON = 'con',
  MODERATOR = 'moderator',
  OBSERVER = 'observer'
}

export enum ParticipantSide {
  PRO = 'pro',
  CON = 'con',
  NEUTRAL = 'neutral',
  MODERATOR = 'moderator'
}

export interface DebateRoom {
  id: string;
  title: string;
  dialogueType: 'debate' | 'free' | 'circular';
  participants: {
    users: string[];
    pro?: string[];
    con?: string[];
    neutral?: string[];
  };
  pro?: string[];
  con?: string[];
  neutral?: string[];
  messages?: ChatMessage[];
  npcDetails?: NpcDetail[];
  moderator?: {
    agent_id?: string;
    name?: string;
    style?: string;
    style_id?: string;
    personality?: string;
  };
  debate_info?: {
    current_stage?: string;
    pro_participants?: string[];
    con_participants?: string[];
    total_turns?: number;
  };
}

export interface ChatMessage {
  id: string;
  text: string;
  sender: string;
  isUser: boolean;
  timestamp: Date;
  isSystemMessage?: boolean;
  role?: string;
  citations?: Citation[];
  skipAnimation?: boolean;
  isGenerating?: boolean;
}

export interface Citation {
  id: string;
  source: string;
  location?: string;
}

export interface NpcDetail {
  id: string;
  name: string;
  portrait_url?: string;
}

export interface DebateState {
  currentStage: DebateStage;
  isUserTurn: boolean;
  turnIndicatorVisible: boolean;
  selectedNpcId: string | null;
  isGeneratingResponse: boolean;
  isGeneratingNext: boolean;
  inputDisabled: boolean;
}

export interface TurnInfo {
  isUserTurn: boolean;
  nextSpeaker?: {
    id: string;
    role: ParticipantRole;
    is_user?: boolean;
  };
}

export interface ModeratorInfo {
  name: string;
  profileImage: string;
}

export interface ParticipantInfo {
  id: string;
  name: string;
  role: ParticipantRole;
  side: ParticipantSide;
  avatar: string;
  isUser: boolean;
  isSelected: boolean;
}

// 소켓 이벤트 관련 타입들
export interface SocketEvents {
  'new-message': (data: { message: ChatMessage; roomId: string }) => void;
  'user_turn': (data: { is_user: boolean; speaker_id?: string }) => void;
  'npc-selected': (data: { npc_id: string; roomId: string }) => void;
  'user_message': (data: { message: string; user_id: string }) => void;
  'next-speaker-update': (data: { roomId: string; nextSpeaker: any }) => void;
}

// 컴포넌트 Props 타입들
export interface DebateChatContainerProps {
  room: DebateRoom;
  messages: ChatMessage[];
  npcDetails: NpcDetail[];
  onSendMessage: (message: string) => void;
  onRefresh: () => void;
  isLoading: boolean;
  isGeneratingResponse: boolean;
  username?: string;
  onEndChat?: () => void;
  userRole?: string;
  onRequestNextMessage?: () => void;
  typingMessageIds?: Set<string>;
  onTypingComplete?: (messageId: string) => void;
  waitingForUserInput?: boolean;
  currentUserTurn?: {speaker_id: string, role: string} | null;
  onProcessUserMessage?: (message: string) => void;
}

export interface ParticipantGridProps {
  room: DebateRoom;
  npcDetails: Record<string, NpcDetail>;
  moderatorInfo: ModeratorInfo;
  selectedNpcId: string | null;
  isUserTurn: boolean;
  userRole: string;
  username: string;
  userProfilePicture: string | null;
}

export interface MessageListProps {
  messages: ChatMessage[];
  room: DebateRoom;
  npcDetails: Record<string, NpcDetail>;
  moderatorInfo: ModeratorInfo;
  typingMessageIds: Set<string>;
  onTypingComplete: (messageId: string) => void;
  username: string;
  userProfilePicture: string | null;
}

export interface MessageInputProps {
  messageText: string;
  setMessageText: (text: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isUserTurn: boolean;
  isInputDisabled: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}

export interface TurnIndicatorProps {
  isUserTurn: boolean;
  turnIndicatorVisible: boolean;
  currentStage: DebateStage;
}

export interface ControlPanelProps {
  onRequestNext: () => void;
  isGeneratingNext: boolean;
  isGeneratingResponse: boolean;
  canShowNextButton: boolean;
} 