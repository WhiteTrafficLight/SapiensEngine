import { Server } from 'socket.io';
import type { NextApiRequest } from 'next';
import type { Socket as NetSocket } from 'net';
import type { Server as HttpServer } from 'http';
import chatService from '@/lib/ai/chatService';

interface SocketServer extends HttpServer {
  io?: Server;
}

interface SocketWithIO extends NetSocket {
  server: SocketServer;
}

interface NextApiResponseWithIO extends NextApiRequest {
  socket: SocketWithIO;
}

// Define interfaces for the socket events
interface JoinRoomData {
  roomId: string | number;
  username: string;
}

interface SendMessageData {
  roomId: string | number;
  message: string;
  sender: string;
}

// Track connected users per room
const connectedUsers: Record<string, string[]> = {};

// Initialize Socket.io server
const SocketHandler = (req: NextApiRequest, res: any) => {
  if (res.socket.server.io) {
    console.log('Socket server already running');
    res.end();
    return;
  }

  const io = new Server(res.socket.server);
  res.socket.server.io = io;

  // Socket.io event handlers
  io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);

    // Join a chat room
    socket.on('join-room', async (data: JoinRoomData) => {
      const { roomId, username } = data;
      const roomIdStr = roomId.toString();

      // Join the socket room
      socket.join(roomIdStr);

      // Add user to the room's connected users list
      if (!connectedUsers[roomIdStr]) {
        connectedUsers[roomIdStr] = [];
      }
      if (!connectedUsers[roomIdStr].includes(username)) {
        connectedUsers[roomIdStr].push(username);
      }

      // Fetch room data from service
      const room = await chatService.getChatRoomById(roomId);
      if (room) {
        // Add user to the room's participants if not already there
        if (!room.participants.users.includes(username)) {
          room.participants.users.push(username);
          room.totalParticipants = room.participants.users.length + room.participants.npcs.length;
        }

        // Notify all clients in the room about the new user
        io.to(roomIdStr).emit('user-joined', {
          username,
          usersInRoom: connectedUsers[roomIdStr],
          participants: room.participants
        });
      }
    });

    // Leave a chat room
    socket.on('leave-room', (data: JoinRoomData) => {
      const { roomId, username } = data;
      const roomIdStr = roomId.toString();

      // Leave the socket room
      socket.leave(roomIdStr);

      // Remove user from the room's connected users list
      if (connectedUsers[roomIdStr]) {
        connectedUsers[roomIdStr] = connectedUsers[roomIdStr].filter(user => user !== username);
        
        // Notify all clients in the room about the user leaving
        io.to(roomIdStr).emit('user-left', {
          username,
          usersInRoom: connectedUsers[roomIdStr]
        });
      }
    });

    // Send a message to a room
    socket.on('send-message', async (data: SendMessageData) => {
      const { roomId, message, sender } = data;
      const roomIdStr = roomId.toString();

      try {
        // Add message to the chat service
        const userMessage = await chatService.sendMessage(roomId, message);
        
        // Broadcast the message to all clients in the room
        io.to(roomIdStr).emit('new-message', userMessage);
        
        // Generate AI response (will be broadcast separately when ready)
        socket.to(roomIdStr).emit('thinking', { sender: roomIdStr });
        
        // Get AI response
        const aiMessage = await chatService.getAIResponse(roomId);
        
        // Broadcast AI response to all clients in the room
        io.to(roomIdStr).emit('new-message', aiMessage);
      } catch (error) {
        console.error('Error sending message:', error);
        socket.emit('error', { message: 'Failed to send message' });
      }
    });

    // Handle disconnection
    socket.on('disconnect', () => {
      console.log('Client disconnected:', socket.id);
      
      // Clean up connected users list (would need to track socket ID to username mapping)
      // This is simplified, in a real app you'd store the rooms a socket has joined
    });
  });

  console.log('Socket server initialized');
  res.end();
};

export default SocketHandler; 