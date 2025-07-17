import React from 'react'

function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-md max-w-md w-full text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-4">
          Screen Share Application
        </h1>
        <p className="text-gray-600 mb-4">
          Use the Python server for screen sharing functionality.
        </p>
        <p className="text-sm text-gray-500">
          Run: <code className="bg-gray-100 px-2 py-1 rounded">python unified_server.py</code>
        </p>
      </div>
    </div>
  )
}

export default App