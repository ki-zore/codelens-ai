import { useState, useEffect } from 'react';
import { useApp } from '../../store/AppContext';
import { api } from '../../services/api';
import { Brain, Plus, Trash2, GitBranch, Upload, Loader2, FolderCode } from 'lucide-react';

export default function Sidebar() {
  const { projects, setProjects, activeProject, setActiveProject, setActiveFile } = useApp();
  const [showIngest, setShowIngest] = useState(false);

  useEffect(() => {
    api.getProjects().then(d => setProjects(d.projects || [])).catch(() => {});
  }, []);

  return (
    <aside className="w-64 h-screen flex flex-col border-r border-border bg-dark-800 shrink-0">
      {/* Logo */}
      <div className="p-4 border-b border-border flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent to-cyan flex items-center justify-center">
          <Brain size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-text-primary">CodeLens AI</h1>
          <p className="text-xs text-text-muted">Codebase Assistant</p>
        </div>
      </div>

      {/* Projects */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">Projects</span>
          <button onClick={() => setShowIngest(!showIngest)}
            className="p-1 rounded hover:bg-dark-600 text-text-secondary hover:text-accent transition-colors">
            <Plus size={16} />
          </button>
        </div>

        {showIngest && <IngestPanel onDone={() => {
          setShowIngest(false);
          api.getProjects().then(d => setProjects(d.projects || []));
        }} />}

        {projects.length === 0 && !showIngest && (
          <div className="text-center py-8">
            <FolderCode size={32} className="mx-auto text-text-muted mb-2 opacity-50" />
            <p className="text-xs text-text-muted">No projects yet</p>
            <button onClick={() => setShowIngest(true)}
              className="mt-2 text-xs text-accent hover:text-accent-light transition-colors">
              + Add a project
            </button>
          </div>
        )}

        <div className="space-y-1">
          {projects.map(p => (
            <button key={p.project_id}
              onClick={() => { setActiveProject(p); setActiveFile(null); }}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all group
                ${activeProject?.project_id === p.project_id
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'hover:bg-dark-600 text-text-secondary hover:text-text-primary border border-transparent'}`}>
              <div className="flex items-center justify-between">
                <span className="truncate font-medium">{p.name}</span>
                <button onClick={(e) => {
                  e.stopPropagation();
                  api.deleteProject(p.project_id)
                    .then(() => api.getProjects().then(d => setProjects(d.projects || [])))
                    .catch(err => console.error("Failed to delete project:", err));
                  if (activeProject?.project_id === p.project_id) setActiveProject(null);
                }} className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose transition-all">
                  <Trash2 size={12} />
                </button>
              </div>
              <div className="flex gap-2 mt-1">
                <span className="text-xs text-text-muted">{p.total_files} files</span>
                {p.languages?.slice(0, 3).map(l => (
                  <span key={l} className="badge bg-dark-600 text-text-muted">{l}</span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}

function IngestPanel({ onDone }) {
  const [mode, setMode] = useState('github');
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGithub = async () => {
    if (!url.trim()) return;
    setLoading(true); setError('');
    try {
      await api.ingestGithub(url.trim());
      onDone();
    } catch (e) { setError(e.message); }
    setLoading(false);
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true); setError('');
    try {
      await api.ingestUpload(file);
      onDone();
    } catch (e) { setError(e.message); }
    setLoading(false);
  };

  return (
    <div className="glass-panel p-3 mb-3 space-y-3">
      <div className="flex gap-1">
        {[['github', GitBranch, 'GitHub'], ['upload', Upload, 'Upload']].map(([m, Icon, label]) => (
          <button key={m} onClick={() => setMode(m)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium transition-colors
              ${mode === m ? 'bg-accent/20 text-accent' : 'text-text-muted hover:text-text-secondary'}`}>
            <Icon size={13} />{label}
          </button>
        ))}
      </div>

      {mode === 'github' ? (
        <div className="space-y-2">
          <input type="text" placeholder="https://github.com/user/repo"
            value={url} onChange={e => setUrl(e.target.value)}
            className="w-full px-3 py-2 bg-dark-900 border border-border rounded-lg text-sm text-text-primary
              placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
            onKeyDown={e => e.key === 'Enter' && handleGithub()} />
          <button onClick={handleGithub} disabled={loading || !url.trim()}
            className="btn-primary w-full text-sm flex items-center justify-center gap-2">
            {loading ? <><Loader2 size={14} className="animate-spin" />Cloning...</> : 'Clone & Analyze'}
          </button>
        </div>
      ) : (
        <label className={`block w-full py-4 border-2 border-dashed border-border rounded-lg text-center cursor-pointer
          hover:border-accent/50 transition-colors ${loading ? 'opacity-50 pointer-events-none' : ''}`}>
          {loading ? <Loader2 size={16} className="mx-auto animate-spin text-accent" />
            : <><Upload size={16} className="mx-auto text-text-muted mb-1" />
              <span className="text-xs text-text-muted">Drop ZIP or click to browse</span></>}
          <input type="file" accept=".zip" className="hidden" onChange={handleUpload} />
        </label>
      )}

      {error && <p className="text-xs text-rose">{error}</p>}
    </div>
  );
}
