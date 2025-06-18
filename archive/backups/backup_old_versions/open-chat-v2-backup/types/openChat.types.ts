export interface ChatRoom {
  id: string;
  title: string;
  context?: string;
  participants: {
    users: string[];
    npcs: string[];
  };
  totalParticipants: number;
  lastActivity: string;
  maxParticipants?: number;
  isPublic?: boolean;
  dialogueType?: 'free' | 'debate' | 'socratic' | 'dialectical';
  pro?: string[];
  con?: string[];
  neutral?: string[];
  moderator?: {
    style_id?: string;
    style?: string;
  };
  npcPositions?: Record<string, 'pro' | 'con'>;
  userDebateRole?: 'pro' | 'con' | 'neutral';
}

export interface Philosopher {
  id: string;
  name: string;
  period?: string; 
  nationality?: string;
  description?: string;
  key_concepts?: string[];
  portrait_url?: string;
}

export interface ChatRoomCreationParams {
  title: string;
  maxParticipants: number;
  npcs: string[];
  isPublic: boolean;
  generateInitialMessage?: boolean;
  dialogueType: 'free' | 'debate' | 'socratic' | 'dialectical';
  username?: string;
  moderator?: {
    style_id: string;
    style: string;
  };
  npcPositions?: Record<string, 'pro' | 'con'>;
  userDebateRole?: 'pro' | 'con' | 'neutral';
  context?: string;
  contextUrl?: string;
  contextFileContent?: string;
}

export interface CreateChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateChat: (params: ChatRoomCreationParams) => Promise<void>;
  isCreating: boolean;
  philosophers: Philosopher[];
  customNpcs: Philosopher[];
}

export interface ChatRoomListProps {
  chatRooms: ChatRoom[];
  isLoading: boolean;
  onRefresh: () => void;
  onJoinChat: (chatId: string) => void;
}

export interface SocketStatus {
  connected: boolean;
  onReconnect: () => void;
}

export interface OpenChatState {
  // Chat rooms
  activeChats: ChatRoom[];
  isLoading: boolean;
  
  // Search and filtering
  searchQuery: string;
  activeTab: 'all' | 'active' | 'recent' | 'popular';
  showParticipants: number | null;
  
  // Modals
  showCreateChatModal: boolean;
  chatToJoin: ChatRoom | null;
  
  // Socket
  socketConnected: boolean;
  
  // User
  username: string;
  
  // Philosophers
  philosophers: Philosopher[];
  customNpcs: Philosopher[];
} 