import React, { useState, useEffect, useRef } from 'react';
import { 
  Monitor, 
  Users, 
  MessageCircle, 
  Settings, 
  Play, 
  Square, 
  Hand, 
  Send,
  Maximize,
  Wifi,
  WifiOff
} from 'lucide-react';

interface User {
  name: string;
  joined_at: number;
}

interface Message {
  user: string;
  text: string;
  timestamp: number;
}

interface ScreenShareSettings {
  fps: number;
  quality: number;
  monitor: number;
}

export default function ScreenShare() {
  const [userId] = useState(() => 'user_' + Math.random().toString(36).substr(2, 9));
  const [users, setUsers] = useState<Record<string, User>>({});
  const [currentPresenter, setCurrentPresenter] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageInput, setMessageInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [settings, setSettings] = useState<ScreenShareSettings>({
    fps: 30,
    quality: 85,
    monitor: 0
  });
  
  const screenFrameRef = useRef<HTMLImageElement>(null);
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  
  const isPresenter = currentPresenter === userId;
  const userName = `User ${userId.slice(-4)}`;

  // API calls
  const apiCall = async (endpoint: string, options?: RequestInit) => {
    try {
      const response = await fetch(`http://localhost:8080${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });
      return response;
    } catch (error) {
      console.error(`API call failed for ${endpoint}:`, error);
      setIsConnected(false);
      throw error;
    }
  };

  const joinRoom = async () => {
    try {
      const response = await apiCall('/api/join', {
        method: 'POST',
        body: JSON.stringify({ userId, name: userName })
      });
      
      if (response.ok) {
        setIsConnected(true);
      }
    } catch (error) {
      console.error('Failed to join room:', error);
    }
  };

  const updateUsers = async () => {
    try {
      const response = await apiCall('/api/users');
      const data = await response.json();
      setUsers(data.users);
      setCurrentPresenter(data.presenter);
    } catch (error) {
      // Silently handle errors during polling
    }
  };

  const updateMessages = async () => {
    try {
      const response = await apiCall('/api/messages');
      const data = await response.json();
      setMessages(data.messages);
    } catch (error) {
      // Silently handle errors during polling
    }
  };

  const updateStatus = async () => {
    try {
      const response = await apiCall('/api/status');
      const data = await response.json();
      setIsSharing(data.sharing);
    } catch (error) {
      // Silently handle errors during polling
    }
  };

  const updateFrame = async () => {
    try {
      const response = await apiCall('/api/frame');
      if (response.ok) {
        const blob = await response.blob();
        if (blob.size > 0 && screenFrameRef.current) {
          const url = URL.createObjectURL(blob);
          screenFrameRef.current.src = url;
        }
      }
    } catch (error) {
      // Silently handle frame update errors
    }
  };

  const startSharing = async () => {
    try {
      await apiCall('/api/start_sharing', {
        method: 'POST',
        body: JSON.stringify({ userId })
      });
    } catch (error) {
      console.error('Failed to start sharing:', error);
    }
  };

  const stopSharing = async () => {
    try {
      await apiCall('/api/stop_sharing', {
        method: 'POST',
        body: JSON.stringify({ userId })
      });
    } catch (error) {
      console.error('Failed to stop sharing:', error);
    }
  };

  const requestPresenter = async () => {
    try {
      await apiCall('/api/request_presenter', {
        method: 'POST',
        body: JSON.stringify({ userId })
      });
    } catch (error) {
      console.error('Failed to request presenter:', error);
    }
  };

  const sendMessage = async () => {
    if (!messageInput.trim()) return;
    
    try {
      await apiCall('/api/message', {
        method: 'POST',
        body: JSON.stringify({
          userId,
          text: messageInput,
          user: userName
        })
      });
      setMessageInput('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const updateSettings = async (newSettings: Partial<ScreenShareSettings>) => {
    const updatedSettings = { ...settings, ...newSettings };
    setSettings(updatedSettings);
    
    try {
      await apiCall('/api/settings', {
        method: 'POST',
        body: JSON.stringify(updatedSettings)
      });
    } catch (error) {
      console.error('Failed to update settings:', error);
    }
  };

  // Effects
  useEffect(() => {
    joinRoom();
  }, []);

  useEffect(() => {
    if (!isConnected) return;

    const pollInterval = setInterval(() => {
      updateUsers();
      updateMessages();
      updateStatus();
    }, 1000);

    const frameInterval = setInterval(() => {
      updateFrame();
    }, 100);

    return () => {
      clearInterval(pollInterval);
      clearInterval(frameInterval);
    };
  }, [isConnected]);

  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto p-6">
        {/* Header */}
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Monitor className="w-8 h-8 text-indigo-600" />
              <h1 className="text-2xl font-bold text-gray-800">Screen Share Pro</h1>
            </div>
            
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                {isConnected ? (
                  <Wifi className="w-5 h-5 text-green-500" />
                ) : (
                  <WifiOff className="w-5 h-5 text-red-500" />
                )}
                <span className={`text-sm font-medium ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Role:</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  isPresenter ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {isPresenter ? 'Presenter' : 'Viewer'}
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-600">{Object.keys(users).length} users</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Video Area */}
          <div className="lg:col-span-3">
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20">
              <div className="relative bg-black rounded-xl overflow-hidden min-h-[400px] flex items-center justify-center">
                {isSharing ? (
                  <img
                    ref={screenFrameRef}
                    alt="Shared Screen"
                    className="max-w-full max-h-[500px] object-contain"
                  />
                ) : (
                  <div className="text-gray-400 text-center">
                    <Monitor className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">No screen being shared</p>
                  </div>
                )}
                
                <button className="absolute top-4 right-4 bg-black/50 hover:bg-black/70 text-white p-2 rounded-lg transition-colors">
                  <Maximize className="w-5 h-5" />
                </button>
              </div>
              
              {/* Controls */}
              <div className="flex gap-3 mt-6">
                {isPresenter && !isSharing && (
                  <button
                    onClick={startSharing}
                    className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    <Play className="w-4 h-4" />
                    Start Sharing
                  </button>
                )}
                
                {isPresenter && isSharing && (
                  <button
                    onClick={stopSharing}
                    className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    <Square className="w-4 h-4" />
                    Stop Sharing
                  </button>
                )}
                
                {!isPresenter && (
                  <button
                    onClick={requestPresenter}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    <Hand className="w-4 h-4" />
                    Request Presenter
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Participants */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20">
              <div className="flex items-center gap-2 mb-4">
                <Users className="w-5 h-5 text-indigo-600" />
                <h3 className="font-semibold text-gray-800">Participants</h3>
              </div>
              
              <div className="space-y-2">
                {Object.entries(users).map(([id, user]) => (
                  <div key={id} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-700">{user.name}</span>
                    {id === currentPresenter && (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                        Presenter
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Chat */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20">
              <div className="flex items-center gap-2 mb-4">
                <MessageCircle className="w-5 h-5 text-indigo-600" />
                <h3 className="font-semibold text-gray-800">Chat</h3>
              </div>
              
              <div
                ref={chatMessagesRef}
                className="h-48 overflow-y-auto bg-gray-50 rounded-lg p-3 mb-3 space-y-2"
              >
                {messages.map((msg, index) => (
                  <div key={index} className="text-sm">
                    <span className="font-medium text-indigo-600">{msg.user}:</span>
                    <span className="ml-2 text-gray-700">{msg.text}</span>
                  </div>
                ))}
              </div>
              
              <div className="flex gap-2">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                  placeholder="Type a message..."
                  className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  maxLength={200}
                />
                <button
                  onClick={sendMessage}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-lg transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Settings */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20">
              <div className="flex items-center gap-2 mb-4">
                <Settings className="w-5 h-5 text-indigo-600" />
                <h3 className="font-semibold text-gray-800">Settings</h3>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">FPS</label>
                  <select
                    value={settings.fps}
                    onChange={(e) => updateSettings({ fps: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  >
                    <option value={15}>15 FPS</option>
                    <option value={30}>30 FPS</option>
                    <option value={60}>60 FPS</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Quality: {settings.quality}%
                  </label>
                  <input
                    type="range"
                    min="50"
                    max="95"
                    value={settings.quality}
                    onChange={(e) => updateSettings({ quality: parseInt(e.target.value) })}
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Monitor</label>
                  <select
                    value={settings.monitor}
                    onChange={(e) => updateSettings({ monitor: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  >
                    <option value={0}>Primary Monitor</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}