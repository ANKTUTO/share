import React from 'react'
import ServerStatus from './components/ServerStatus'
import ScreenShare from './components/ScreenShare'

function App() {
  const [serverRunning, setServerRunning] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    const checkServer = async () => {
      try {
        const response = await fetch('http://localhost:8080/api/status');
        setServerRunning(response.ok);
      } catch (error) {
        setServerRunning(false);
      }
    };

    checkServer();
    const interval = setInterval(checkServer, 5000);
    return () => clearInterval(interval);
  }, []);

  if (serverRunning === null) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <>
      {serverRunning ? <ScreenShare /> : <ServerStatus />}
    </>
  )
}

export default App