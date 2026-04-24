import { useState, useEffect } from 'react';
import { useApp } from '../../store/AppContext';
import { api } from '../../services/api';
import { ChevronRight, ChevronDown, FileCode, Folder, FolderOpen } from 'lucide-react';

const LANG_COLORS = {
  python: '#3572A5', javascript: '#f1e05a', typescript: '#3178c6', java: '#b07219',
  go: '#00ADD8', rust: '#dea584', ruby: '#701516', css: '#563d7c', html: '#e34c26',
  json: '#6d8086', markdown: '#083fa1', yaml: '#cb171e',
};

export default function FileExplorer() {
  const { activeProject, setActiveFile } = useApp();
  const [tree, setTree] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeProject) return;
    setLoading(true);
    api.getFileTree(activeProject.project_id)
      .then(setTree)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeProject?.project_id]);

  if (!activeProject) {
    return (
      <div className="h-full flex items-center justify-center text-center p-4">
        <p className="text-xs text-text-muted">Select a project to browse files</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-3 space-y-2">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="skeleton h-6 rounded" style={{ width: `${60 + Math.random() * 30}%` }} />
        ))}
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-2">
      {tree?.children?.map((node, i) => (
        <TreeNode key={i} node={node} depth={0} onSelect={setActiveFile} />
      ))}
    </div>
  );
}

function TreeNode({ node, depth, onSelect }) {
  const [expanded, setExpanded] = useState(depth < 1);

  if (node.type === 'file') {
    const color = LANG_COLORS[node.language] || '#64748b';
    return (
      <button
        onClick={() => onSelect({ path: node.path, language: node.language })}
        className="w-full flex items-center gap-1.5 py-1 px-2 rounded text-xs hover:bg-dark-600
          text-text-secondary hover:text-text-primary transition-colors"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        <FileCode size={13} style={{ color }} className="shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 py-1 px-2 rounded text-xs hover:bg-dark-600
          text-text-secondary hover:text-text-primary transition-colors font-medium"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {expanded ? <FolderOpen size={13} className="text-amber shrink-0" /> : <Folder size={13} className="text-amber shrink-0" />}
        <span className="truncate">{node.name}</span>
        <span className="text-text-muted ml-auto">{node.children?.length || 0}</span>
      </button>
      {expanded && node.children?.map((child, i) => (
        <TreeNode key={i} node={child} depth={depth + 1} onSelect={onSelect} />
      ))}
    </div>
  );
}
