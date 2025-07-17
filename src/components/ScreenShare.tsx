import React, { useState, useEffect, useRef } from 'react';
import { 
  Monitor, 
  Play, 
  Square, 
  Settings, 
  Users, 
  Mic, 
  MicOff, 
  Video, 
  VideoOff,
  PhoneOff,
  Copy,
  Maximize2,
  Minimize2
} from 'lucide-react';

interface QualityPreset {
  name: string;
  fps: number;
  resolution: { width: number; height: number };
  bitrate: number;
}

const qualityPresets: QualityPreset[] = [
  { name: 'Ultra HD', fps: 60, resolution: { width: 1920, height: 1080 }, bitrate: 8000 },
  { name: 'High', fps: 60, resolution: { width: 1280, height: 720 }, bitrate: 5000 },
  { name: 'Medium', fps: 30, resolution: { width: 1280, height: 720 }, bitrate: 3000 },
  { name: 'Low', fps: 30, resolution: { width: 854, height: 480 }, bitrate: 1500 },
  { name: 'Data Saver', fps: 15, resolution: { width: 640, height: 360 }, bitrate: 800 },
];

export default function ScreenShare() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [selectedQuality, setSelectedQuality] = useState(qualityPresets[1]);
  const [micEnabled, setMicEnabled] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [participants] = useState(1);
  const [meetingId] = useState('abc-defg-hij');
  const [stats, setStats] = useState({ 
    fps: 0, 
    resolution: '1280x720', 
    bitrate: '0 kbps',
    latency: '0ms',
    packetLoss: '0%'
  });
  
  const streamImageRef = useRef<HTMLImageElement>(null);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const frameCountRef = useRef(0);
  const lastFrameTimeRef = useRef(Date.now());

  // Connect to Python server stream
  const connectToStream = async () => {
    try {
      setIsConnected(true);
      
      // Start polling for frames
      streamIntervalRef.current = setInterval(async () => {
        try {
          const response = await fetch('http://localhost:8080/stream');
          if (!response.ok) throw new Error('Stream unavailable');
          
          const data = await response.json();
          if (data.frame && streamImageRef.current) {
            streamImageRef.current.src = 'data:image/jpeg;base64,' + data.frame;
            updateFPS();
          }
        } catch (error) {
          console.error('Frame fetch error:', error);
        }
      }, 1000 / 30); // 30 FPS polling
      
    } catch (error) {
      console.error('Connection failed:', error);
      setIsConnected(false);
    }
  };

  // Start streaming (tells Python server to start capture)
  const startStreaming = async () => {
    try {
      // Update quality settings on server
      await fetch('http://localhost:8080/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fps: selectedQuality.fps,
          resolution: [selectedQuality.resolution.width, selectedQuality.resolution.height],
          bitrate: selectedQuality.bitrate
        })
      });
      
      setIsStreaming(true);
      
      // Connect to stream if not already connected
      if (!isConnected) {
        await connectToStream();
      }
      
      setStats(prev => ({
        ...prev,
        fps: selectedQuality.fps,
        resolution: `${selectedQuality.resolution.width}x${selectedQuality.resolution.height}`,
        bitrate: `${selectedQuality.bitrate} kbps`
      }));
      
    } catch (error) {
      console.error('Failed to start streaming:', error);
    }
  };

  const stopStreaming = () => {
    setIsStreaming(false);
    setIsConnected(false);
    
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
    
    if (streamImageRef.current) {
      streamImageRef.current.src = '';
    }
  };

  const updateFPS = () => {
    frameCountRef.current++;
    const now = Date.now();
    const elapsed = (now - lastFrameTimeRef.current) / 1000;
    
    if (elapsed >= 1) {
      const fps = frameCountRef.current / elapsed;
      setStats(prev => ({ ...prev, fps: Math.round(fps) }));
      frameCountRef.current = 0;
      lastFrameTimeRef.current = now;
    }
  };

  const copyMeetingLink = () => {
    navigator.clipboard.writeText(`http://localhost:8080`);
  };

  const updateQuality = async (preset: QualityPreset) => {
    setSelectedQuality(preset);
    
    if (isStreaming) {
      try {
        await fetch('http://localhost:8080/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fps: preset.fps,
            resolution: [preset.resolution.width, preset.resolution.height],
            bitrate: preset.bitrate
          })
        });
      } catch (error) {
        console.error('Failed to update quality:', error);
      }
    }
  };

  useEffect(() => {
    return () => {
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Top Bar */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Monitor className="w-6 h-6 text-blue-400" />
              <span className="text-white font-semibold">Screen Share Pro</span>
            </div>
            <div className="text-gray-400 text-sm">
              Meeting ID: {meetingId}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={copyMeetingLink}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
            >
              <Copy className="w-4 h-4" />
              Copy Viewer Link
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Video Area */}
        <div className="flex-1 flex flex-col">
          {/* Main Video */}
          <div className="flex-1 bg-black relative">
            {isConnected ? (
              <div className="w-full h-full flex items-center justify-center relative">
                <img
                  ref={streamImageRef}
                  className="w-full h-full object-contain"
                  alt="Screen Stream"
                />
                
                {/* Video Overlay Controls */}
                <div className="absolute top-4 left-4 bg-black/70 backdrop-blur-sm rounded-lg px-3 py-2">
                  <div className="flex items-center gap-2 text-white text-sm">
                    <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-red-500 animate-pulse' : 'bg-gray-500'}`}></div>
                    <span>{isStreaming ? 'LIVE' : 'CONNECTED'} • {stats.fps} FPS • {stats.resolution}</span>
                  </div>
                </div>

                <div className="absolute top-4 right-4 flex gap-2">
                  <button
                    onClick={() => setShowSettings(!showSettings)}
                    className="p-2 bg-black/70 hover:bg-black/90 text-white rounded-lg transition-colors backdrop-blur-sm"
                    title="Settings"
                  >
                    <Settings className="w-5 h-5" />
                  </button>
                </div>

                {/* Performance Stats Overlay */}
                <div className="absolute bottom-4 left-4 bg-black/70 backdrop-blur-sm rounded-lg p-3 text-white text-xs">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    <div>FPS: <span className="text-green-400">{stats.fps}</span></div>
                    <div>Bitrate: <span className="text-blue-400">{stats.bitrate}</span></div>
                    <div>Latency: <span className="text-yellow-400">{stats.latency}</span></div>
                    <div>Loss: <span className="text-red-400">{stats.packetLoss}</span></div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <Monitor className="w-24 h-24 mx-auto mb-4 opacity-50" />
                  <h3 className="text-xl font-semibold mb-2">Ready to Share Screen</h3>
                  <p className="text-gray-500 mb-4">Click "Start Sharing" to begin streaming at {selectedQuality.fps} FPS</p>
                  <div className="text-sm">
                    Quality: <span className="text-blue-400">{selectedQuality.name}</span> • 
                    Resolution: <span className="text-green-400">{selectedQuality.resolution.width}×{selectedQuality.resolution.height}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Controls */}
          <div className="bg-gray-800 border-t border-gray-700 px-6 py-4">
            <div className="flex items-center justify-between">
              {/* Left Controls */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setMicEnabled(!micEnabled)}
                  className={`p-3 rounded-full transition-colors ${
                    micEnabled 
                      ? 'bg-gray-700 hover:bg-gray-600 text-white' 
                      : 'bg-red-600 hover:bg-red-700 text-white'
                  }`}
                  title={micEnabled ? 'Mute' : 'Unmute'}
                >
                  {micEnabled ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
                </button>

                <button
                  onClick={() => setCameraEnabled(!cameraEnabled)}
                  className={`p-3 rounded-full transition-colors ${
                    cameraEnabled 
                      ? 'bg-gray-700 hover:bg-gray-600 text-white' 
                      : 'bg-red-600 hover:bg-red-700 text-white'
                  }`}
                  title={cameraEnabled ? 'Turn off camera' : 'Turn on camera'}
                >
                  {cameraEnabled ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
                </button>
              </div>

              {/* Center Controls */}
              <div className="flex items-center gap-4">
                <button
                  onClick={isStreaming ? stopStreaming : startStreaming}
                  className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all ${
                    isStreaming
                      ? 'bg-red-600 hover:bg-red-700 text-white'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
                >
                  {isStreaming ? (
                    <>
                      <Square className="w-5 h-5" />
                      Stop Sharing
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5" />
                      Start Sharing
                    </>
                  )}
                </button>
              </div>

              {/* Right Controls */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 text-gray-400">
                  <Users className="w-5 h-5" />
                  <span>{participants}</span>
                </div>

                <button className="p-3 bg-red-600 hover:bg-red-700 text-white rounded-full transition-colors">
                  <PhoneOff className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="w-80 bg-gray-800 border-l border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-white font-semibold">Stream Settings</h3>
              <button
                onClick={() => setShowSettings(false)}
                className="text-gray-400 hover:text-white"
              >
                ×
              </button>
            </div>

            <div className="space-y-6">
              {/* Quality Presets */}
              <div>
                <label className="block text-gray-300 text-sm font-medium mb-3">
                  Quality Preset
                </label>
                <div className="space-y-2">
                  {qualityPresets.map((preset) => (
                    <button
                      key={preset.name}
                      onClick={() => updateQuality(preset)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        selectedQuality.name === preset.name
                          ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                          : 'border-gray-600 bg-gray-700 text-gray-300 hover:border-gray-500'
                      }`}
                    >
                      <div className="font-medium">{preset.name}</div>
                      <div className="text-sm opacity-75">
                        {preset.resolution.width}×{preset.resolution.height} • {preset.fps} FPS • {preset.bitrate} kbps
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Connection Info */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="text-gray-300 font-medium mb-2">Connection Status</h4>
                <div className="space-y-1 text-sm text-gray-400">
                  <div>Server: localhost:8080</div>
                  <div>Protocol: HTTP Streaming</div>
                  <div>Format: JPEG</div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                    <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
                  </div>
                </div>
              </div>

              {/* Instructions */}
              <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
                <h4 className="text-blue-300 font-medium mb-2">How to Share</h4>
                <div className="text-sm text-blue-200 space-y-1">
                  <p>1. Make sure Python server is running</p>
                  <p>2. Click "Start Sharing" above</p>
                  <p>3. Share viewer link with others</p>
                  <p>4. Others visit: localhost:8080</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}