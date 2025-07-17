import React, { useState, useEffect, useRef } from 'react';
import { Monitor, Users, MessageCircle, Settings, Play, Square, Send, Maximize, Wifi, WifiOff, User, X, Chrome, AppWindow as WindowIcon, MonitorSpeaker } from 'lucide-react';

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

interface ShareSource {
  id: string;
  name: string;
  type: 'screen' | 'window' | 'tab';
  thumbnail?: string;
}

export default function ScreenShare() {
  const [userId] = useState(() => 'user_' + Math.random().toString(36).substr(2, 9));
  const [users, setUsers] = useState<Record<string, User>>({});
  const [currentSharer, setCurrentSharer] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageInput, setMessageInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareTab, setShareTab] = useState<'tab' | 'window' | 'screen'>('screen');
  const [availableSources, setAvailableSources] = useState<ShareSource[]>([]);
  const [selectedSource, setSelectedSource] = useState<ShareSource | null>(null);
  const [settings, setSettings] = useState<ScreenShareSettings>({
    fps: 30,
    quality: 85,
    monitor: 0
  });
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout>();
  
  const userName = `User ${userId.slice(-4)}`;
  const amISharing = currentSharer === userId;
  const amIPresenter = currentSharer === userId || !currentSharer;

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
      setCurrentSharer(data.presenter);
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

  const getAvailableSources = async () => {
    try {
      // Get available media sources
      const sources = await (navigator.mediaDevices as any).getDisplayMedia({
        video: true,
        audio: true,
        systemAudio: 'include'
      }).then((stream: MediaStream) => {
        // Stop the stream immediately as we just wanted to trigger permission
        stream.getTracks().forEach(track => track.stop());
        return [];
      }).catch(() => []);

      // For demo purposes, create mock sources
      const mockSources: ShareSource[] = [
        {
          id: 'screen-1',
          name: 'Entire Screen',
          type: 'screen'
        },
        {
          id: 'window-1',
          name: 'Chrome Browser',
          type: 'window'
        },
        {
          id: 'window-2',
          name: 'VS Code',
          type: 'window'
        },
        {
          id: 'tab-1',
          name: 'Screen Share Pro',
          type: 'tab'
        },
        {
          id: 'tab-2',
          name: 'Google Meet',
          type: 'tab'
        }
      ];

      setAvailableSources(mockSources);
    } catch (error) {
      console.error('Failed to get available sources:', error);
    }
  };

  const captureAndSendFrame = () => {
    if (!streamRef.current || !canvasRef.current || !isSharing || !videoRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const video = videoRef.current;
    
    // Set canvas dimensions to match video
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const sendFrame = () => {
      if (!isSharing || !streamRef.current || !video.videoWidth) return;

      try {
        // Draw current video frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert canvas to blob and send to server
        canvas.toBlob(async (blob) => {
          if (blob && isSharing) {
            const formData = new FormData();
            formData.append('frame', blob);
            formData.append('userId', userId);

            try {
              await fetch('http://localhost:8080/api/frame', {
                method: 'POST',
                body: formData
              });
            } catch (error) {
              console.error('Failed to send frame:', error);
            }
          }
        }, 'image/jpeg', settings.quality / 100);
      } catch (error) {
        console.error('Failed to capture frame:', error);
      }
    };

    // Start frame capture interval
    frameIntervalRef.current = setInterval(sendFrame, 1000 / settings.fps);
  };

  const startSharing = async (source?: ShareSource) => {
    try {
      let constraints: any = {
        video: {
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          frameRate: { ideal: settings.fps }
        },
        audio: true
      };

      // Configure constraints based on source type
      if (source?.type === 'screen') {
        constraints.video.mediaSource = 'screen';
      } else if (source?.type === 'window') {
        constraints.video.mediaSource = 'window';
      } else if (source?.type === 'tab') {
        constraints.video.mediaSource = 'tab';
      }

      // Get screen share stream from browser
      const stream = await navigator.mediaDevices.getDisplayMedia(constraints);

      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      // Notify server that we're sharing
      await apiCall('/api/start_sharing', {
        method: 'POST',
        body: JSON.stringify({ userId })
      });

      setIsSharing(true);
      setShowShareModal(false);

      // Start capturing and sending frames after video is ready
      setTimeout(() => {
        if (videoRef.current && videoRef.current.readyState >= 2) {
          captureAndSendFrame();
        } else {
          videoRef.current?.addEventListener('loadeddata', captureAndSendFrame, { once: true });
        }
      }, 1000);

      // Handle stream end (when user stops sharing via browser)
      stream.getVideoTracks()[0].addEventListener('ended', () => {
        stopSharing();
      });

    } catch (error) {
      console.error('Failed to start screen sharing:', error);
      if (error instanceof Error && error.name === 'NotAllowedError') {
        alert('Screen sharing permission denied. Please allow screen sharing and try again.');
      } else {
        alert('Screen sharing failed. Please try again.');
      }
      setShowShareModal(false);
    }
  };

  const stopSharing = async () => {
    try {
      // Stop the media stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }

      // Clear frame interval
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }

      // Notify server that we stopped sharing
      await apiCall('/api/stop_sharing', {
        method: 'POST',
        body: JSON.stringify({ userId })
      });

      setIsSharing(false);
    } catch (error) {
      console.error('Failed to stop sharing:', error);
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

  const toggleFullscreen = () => {
    const element = videoRef.current;
    if (element) {
      if (!document.fullscreenElement) {
        element.requestFullscreen?.() || (element as any).webkitRequestFullscreen?.();
      } else {
        document.exitFullscreen?.() || (document as any).webkitExitFullscreen?.();
      }
    }
  };

  // Load shared screen from server
  const loadSharedScreen = async () => {
    if (currentSharer && currentSharer !== userId) {
      try {
        const response = await fetch('http://localhost:8080/api/frame');
        if (response.ok) {
          const blob = await response.blob();
          if (blob.size > 0) {
            const url = URL.createObjectURL(blob);
            
            if (videoRef.current) {
              const img = videoRef.current as any;
              img.src = url;
              img.style.display = 'block';
              
              // Clean up previous URL
              setTimeout(() => URL.revokeObjectURL(url), 100);
            }
          }
        }
      } catch (error) {
        // Silently handle frame loading errors
      }
    } else if (!currentSharer && videoRef.current && !isSharing) {
      // Clear the display when no one is sharing
      videoRef.current.srcObject = null;
      (videoRef.current as any).src = '';
    }
  };

  const openShareModal = () => {
    setShowShareModal(true);
    getAvailableSources();
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'screen':
        return <MonitorSpeaker className="w-6 h-6" />;
      case 'window':
        return <WindowIcon className="w-6 h-6" />;
      case 'tab':
        return <Chrome className="w-6 h-6" />;
      default:
        return <Monitor className="w-6 h-6" />;
    }
  };

  const getFilteredSources = () => {
    return availableSources.filter(source => source.type === shareTab);
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
      if (!isSharing) {
        loadSharedScreen();
      }
    }, 1000);

    return () => {
      clearInterval(pollInterval);
    };
  }, [isConnected, isSharing]);

  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto p-6">
        {/* Header */}
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Monitor className="w-8 h-8 text-indigo-600" />
              <h1 className="text-2xl font-bold text-gray-800">Screen Share Pro</h1>
              <div className="ml-4 px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm font-medium flex items-center gap-2">
                <User className="w-4 h-4" />
                {userName}
              </div>
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
                <span className="text-sm text-gray-600">Status:</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  isSharing ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {isSharing ? 'Presenting' : amIPresenter ? 'Presenter' : 'Viewer'}
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
                {isSharing || currentSharer ? (
                  <>
                    {isSharing ? (
                      <video
                        ref={videoRef}
                        autoPlay
                        muted
                        className="max-w-full max-h-[500px] object-contain"
                      />
                    ) : (
                      <img
                        ref={videoRef as any}
                        className="max-w-full max-h-[500px] object-contain"
                        alt="Shared screen"
                      />
                    )}
                  </>
                ) : (
                  <div className="text-gray-400 text-center">
                    <Monitor className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">No screen being shared</p>
                    <p className="text-sm mt-2">Click "Present Screen" to share your screen</p>
                  </div>
                )}
                
                {(isSharing || currentSharer) && (
                  <button 
                    onClick={toggleFullscreen}
                    className="absolute top-4 right-4 bg-black/50 hover:bg-black/70 text-white p-2 rounded-lg transition-colors"
                  >
                    <Maximize className="w-5 h-5" />
                  </button>
                )}
              </div>
              
              {/* Controls */}
              <div className="flex gap-3 mt-6">
                {!isSharing ? (
                  <button
                    onClick={openShareModal}
                    disabled={!amIPresenter}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg transition-colors font-medium"
                  >
                    <MonitorSpeaker className="w-5 h-5" />
                    Present Screen
                  </button>
                ) : (
                  <button
                    onClick={stopSharing}
                    className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg transition-colors font-medium"
                  >
                    <Square className="w-5 h-5" />
                    Stop Presenting
                  </button>
                )}
                
                {!amIPresenter && (
                  <button
                    onClick={() => apiCall('/api/request_presenter', {
                      method: 'POST',
                      body: JSON.stringify({ userId })
                    })}
                    className="flex items-center gap-2 bg-gray-600 hover:bg-gray-700 text-white px-6 py-3 rounded-lg transition-colors font-medium"
                  >
                    <User className="w-5 h-5" />
                    Request Presenter
                  </button>
                )}
              </div>

              {/* Hidden canvas for frame capture */}
              <canvas ref={canvasRef} style={{ display: 'none' }} />
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
                    {id === currentSharer && (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                        Presenting
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target FPS</label>
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
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Share Screen Modal */}
      {showShareModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-800">Choose what to share</h2>
                <button
                  onClick={() => setShowShareModal(false)}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                The site will be able to see the contents of your screen
              </p>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-gray-200">
              <button
                onClick={() => setShareTab('tab')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  shareTab === 'tab'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Chrome Tab
              </button>
              <button
                onClick={() => setShareTab('window')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  shareTab === 'window'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Window
              </button>
              <button
                onClick={() => setShareTab('screen')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  shareTab === 'screen'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Entire Screen
              </button>
            </div>

            {/* Source Selection */}
            <div className="p-6 max-h-96 overflow-y-auto">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {getFilteredSources().map((source) => (
                  <button
                    key={source.id}
                    onClick={() => setSelectedSource(source)}
                    className={`p-4 border-2 rounded-lg transition-all hover:shadow-md ${
                      selectedSource?.id === source.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="aspect-video bg-gray-100 rounded-lg mb-3 flex items-center justify-center">
                      {getSourceIcon(source.type)}
                    </div>
                    <p className="text-sm font-medium text-gray-800 truncate">
                      {source.name}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setShowShareModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => selectedSource && startSharing(selectedSource)}
                disabled={!selectedSource}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors font-medium"
              >
                Share
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}