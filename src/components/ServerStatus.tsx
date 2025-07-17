import React, { useState, useEffect } from 'react';
import { Server, AlertCircle, CheckCircle, Terminal, ExternalLink } from 'lucide-react';

export default function ServerStatus() {
  const [serverRunning, setServerRunning] = useState(false);
  const [checking, setChecking] = useState(true);

  const checkServerStatus = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/status');
      setServerRunning(response.ok);
    } catch (error) {
      setServerRunning(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkServerStatus();
    const interval = setInterval(checkServerStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  if (checking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-8 shadow-lg border border-white/20 max-w-md w-full text-center">
          <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Checking server status...</p>
        </div>
      </div>
    );
  }

  if (serverRunning) {
    return null; // Server is running, don't show this component
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-6">
      <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-8 shadow-lg border border-white/20 max-w-2xl w-full">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Server className="w-8 h-8 text-indigo-600" />
            <h1 className="text-2xl font-bold text-gray-800">Screen Share Pro</h1>
          </div>
          
          <div className="flex items-center justify-center gap-2 mb-6">
            <AlertCircle className="w-5 h-5 text-amber-500" />
            <span className="text-amber-600 font-medium">Python Server Required</span>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Terminal className="w-5 h-5" />
              Quick Start
            </h2>
            
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600 mb-2">1. Install Python dependencies:</p>
                <div className="bg-gray-800 text-green-400 p-3 rounded-lg font-mono text-sm">
                  pip install -r requirements.txt
                </div>
              </div>
              
              <div>
                <p className="text-sm text-gray-600 mb-2">2. Start the Python server:</p>
                <div className="bg-gray-800 text-green-400 p-3 rounded-lg font-mono text-sm">
                  python unified_server.py
                </div>
              </div>
              
              <div>
                <p className="text-sm text-gray-600 mb-2">3. Access the application:</p>
                <div className="bg-gray-800 text-blue-400 p-3 rounded-lg font-mono text-sm">
                  http://localhost:8080
                </div>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 rounded-xl p-6">
            <h3 className="font-semibold text-blue-800 mb-3">🚀 Features</h3>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Multi-user screen sharing (like Google Meet)</li>
              <li>• Real-time chat system</li>
              <li>• Presenter role management</li>
              <li>• Quality controls (FPS, resolution, compression)</li>
              <li>• Cross-browser compatibility</li>
              <li>• 60 FPS high-performance streaming</li>
            </ul>
          </div>

          <div className="bg-amber-50 rounded-xl p-6">
            <h3 className="font-semibold text-amber-800 mb-3">🧪 Testing Multi-User</h3>
            <ul className="text-sm text-amber-700 space-y-1">
              <li>• Open multiple browser tabs</li>
              <li>• Use different browsers (Chrome, Firefox, Safari)</li>
              <li>• Try incognito/private windows</li>
              <li>• Test on different devices (same network)</li>
            </ul>
          </div>

          <div className="text-center">
            <button
              onClick={checkServerStatus}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg transition-colors flex items-center gap-2 mx-auto"
            >
              <CheckCircle className="w-5 h-5" />
              Check Server Status
            </button>
          </div>

          <div className="text-center pt-4 border-t border-gray-200">
            <a
              href="http://localhost:8080"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 hover:text-indigo-700 text-sm flex items-center gap-1 justify-center"
            >
              <ExternalLink className="w-4 h-4" />
              Open Python Server Interface
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}