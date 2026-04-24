import { useState, useEffect } from 'react';
import { useApp } from '../../store/AppContext';
import { api } from '../../services/api';
import Editor from '@monaco-editor/react';
import { X, FileCode, Box, ArrowUpRight } from 'lucide-react';

export default function CodeViewer() {
  const { activeProject, activeFile, setActiveFile } = useApp();
  const [fileData, setFileData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeProject || !activeFile?.path) return;
    setLoading(true);
    api.getFileContent(activeProject.project_id, activeFile.path)
      .then(setFileData)
      .catch(() => setFileData(null))
      .finally(() => setLoading(false));
  }, [activeProject?.project_id, activeFile?.path]);

  if (!activeFile) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8">
        <FileCode size={40} className="text-text-muted opacity-30 mb-3" />
        <p className="text-sm text-text-muted">Select a file to view its contents</p>
      </div>
    );
  }

  const langMap = { python: 'python', javascript: 'javascript', typescript: 'typescript', java: 'java',
    go: 'go', rust: 'rust', css: 'css', html: 'html', json: 'json', markdown: 'markdown', yaml: 'yaml' };

  return (
    <div className="h-full flex flex-col">
      {/* File tab bar */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-border bg-dark-800 shrink-0">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-dark-700 border border-border text-sm">
          <FileCode size={14} className="text-accent" />
          <span className="text-text-primary">{activeFile.path}</span>
          <button onClick={() => setActiveFile(null)} className="ml-2 text-text-muted hover:text-rose transition-colors">
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 min-h-0">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="skeleton w-3/4 h-64 rounded-lg" />
          </div>
        ) : fileData ? (
          <Editor
            height="100%"
            language={langMap[fileData.language] || 'plaintext'}
            value={fileData.content}
            theme="vs-dark"
            options={{
              readOnly: true, fontSize: 13, minimap: { enabled: true },
              scrollBeyondLastLine: false, padding: { top: 12 },
              lineNumbers: 'on', renderLineHighlight: 'line',
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              fontLigatures: true,
            }}
            onMount={(editor) => {
              if (activeFile.line) {
                editor.revealLineInCenter(activeFile.line);
                editor.setPosition({ lineNumber: activeFile.line, column: 1 });
              }
            }}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-text-muted text-sm">Failed to load file</div>
        )}
      </div>

      {/* Symbols bar */}
      {fileData && (fileData.functions?.length > 0 || fileData.classes?.length > 0) && (
        <div className="border-t border-border px-3 py-2 flex gap-4 overflow-x-auto shrink-0 bg-dark-800">
          {fileData.classes?.map((c, i) => (
            <span key={`c${i}`} className="badge bg-emerald/15 text-emerald whitespace-nowrap">
              <Box size={10} />{c.name}
            </span>
          ))}
          {fileData.functions?.map((f, i) => (
            <span key={`f${i}`} className="badge bg-cyan/15 text-cyan whitespace-nowrap cursor-pointer hover:bg-cyan/25 transition-colors"
              onClick={() => setActiveFile({ ...activeFile, line: f.start_line })}>
              <ArrowUpRight size={10} />{f.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
