import { createContext, useContext, useState, useCallback } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [activeFile, setActiveFile] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarTab, setSidebarTab] = useState('files'); // 'files' | 'graph'
  const [rightPanel, setRightPanel] = useState('code');  // 'code' | 'graph'

  const addMessage = useCallback((msg) => {
    setChatHistory(prev => [...prev, msg]);
  }, []);

  const clearChat = useCallback(() => setChatHistory([]), []);

  return (
    <AppContext.Provider value={{
      projects, setProjects,
      activeProject, setActiveProject,
      activeFile, setActiveFile,
      chatHistory, setChatHistory, addMessage, clearChat,
      isLoading, setIsLoading,
      sidebarTab, setSidebarTab,
      rightPanel, setRightPanel,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
};
