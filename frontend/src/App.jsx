import { useState } from 'react';
import { AppProvider, useApp } from './store/AppContext';
import Sidebar from './components/Layout/Sidebar';
import ChatPanel from './components/Chat/ChatPanel';
import FileExplorer from './components/FileExplorer/FileExplorer';
import CodeViewer from './components/CodeViewer/CodeViewer';
import GraphView from './components/GraphView/GraphView';
import { FolderTree, GitGraph, Code, MessageSquare } from 'lucide-react';

function AppContent() {
  const { activeProject, rightPanel, setRightPanel } = useApp();
  const [leftTab, setLeftTab] = useState('files'); // 'files' | 'chat'

  return (
    <div className="flex h-screen bg-dark-900 overflow-hidden">
      {/* Sidebar — project list */}
      <Sidebar />

      {/* Main area */}
      <div className="flex-1 flex min-w-0">
        {/* Left panel: Chat + File Explorer */}
        <div className="w-[420px] flex flex-col border-r border-border shrink-0">
          {/* Tab bar */}
          <div className="flex border-b border-border bg-dark-800 shrink-0">
            {[
              ['chat', MessageSquare, 'Chat'],
              ['files', FolderTree, 'Files'],
            ].map(([key, Icon, label]) => (
              <button key={key} onClick={() => setLeftTab(key)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-semibold
                  border-b-2 transition-colors
                  ${leftTab === key
                    ? 'border-accent text-accent bg-accent/5'
                    : 'border-transparent text-text-muted hover:text-text-secondary'}`}>
                <Icon size={14} />{label}
              </button>
            ))}
          </div>

          <div className="flex-1 min-h-0">
            {leftTab === 'chat' ? <ChatPanel /> : <FileExplorer />}
          </div>
        </div>

        {/* Right panel: Code viewer or Graph */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Tab bar */}
          <div className="flex border-b border-border bg-dark-800 shrink-0">
            {[
              ['code', Code, 'Code'],
              ['graph', GitGraph, 'Dependencies'],
            ].map(([key, Icon, label]) => (
              <button key={key} onClick={() => setRightPanel(key)}
                className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold
                  border-b-2 transition-colors
                  ${rightPanel === key
                    ? 'border-accent text-accent bg-accent/5'
                    : 'border-transparent text-text-muted hover:text-text-secondary'}`}>
                <Icon size={14} />{label}
              </button>
            ))}

            {activeProject && (
              <div className="ml-auto flex items-center gap-2 px-4">
                <span className="text-xs text-text-muted">
                  {activeProject.total_files} files · {activeProject.languages?.join(', ')}
                </span>
              </div>
            )}
          </div>

          <div className="flex-1 min-h-0">
            {rightPanel === 'code' ? <CodeViewer /> : <GraphView />}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
