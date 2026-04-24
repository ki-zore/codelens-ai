import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useApp } from '../../store/AppContext';
import { api } from '../../services/api';
import ForceGraph2D from 'react-force-graph-2d';
import { Loader2, Maximize2, ZoomIn, ZoomOut } from 'lucide-react';

const TYPE_COLORS = {
  file: '#6c63ff', function: '#00d4ff', class: '#10b981', unknown: '#64748b',
};
const EDGE_COLORS = {
  imports: '#f59e0b', calls: '#00d4ff', contains: '#374151', inherits: '#f43f5e',
};

export default function GraphView() {
  const { activeProject, setActiveFile } = useApp();
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all' | 'file' | 'function' | 'class'
  const graphRef = useRef();

  useEffect(() => {
    if (!activeProject) return;
    setLoading(true);
    Promise.all([
      api.getGraph(activeProject.project_id),
      api.getGraphStats(activeProject.project_id).catch(() => null),
    ]).then(([g, s]) => { setGraphData(g); setStats(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeProject?.project_id]);

  const filteredData = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };
    let nodes = graphData.nodes || [];
    if (filter !== 'all') nodes = nodes.filter(n => n.type === filter);
    const nodeIds = new Set(nodes.map(n => n.id));
    const links = (graphData.edges || [])
      .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map(e => ({ ...e, source: e.source, target: e.target }));
    return { nodes, links };
  }, [graphData, filter]);

  const handleNodeClick = useCallback((node) => {
    if (node.file_path) setActiveFile({ path: node.file_path, line: node.line_number });
    else if (node.type === 'file') setActiveFile({ path: node.id });
  }, [setActiveFile]);

  const paintNode = useCallback((node, ctx) => {
    const r = node.type === 'file' ? 6 : 4;
    const color = TYPE_COLORS[node.type] || TYPE_COLORS.unknown;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = color + '60';
    ctx.lineWidth = 2;
    ctx.stroke();
    // Label
    ctx.font = '3px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(node.label?.slice(0, 20) || '', node.x, node.y + r + 5);
  }, []);

  if (!activeProject) {
    return <div className="h-full flex items-center justify-center text-sm text-text-muted">Select a project</div>;
  }

  if (loading) {
    return <div className="h-full flex items-center justify-center">
      <Loader2 size={24} className="animate-spin text-accent" />
    </div>;
  }

  return (
    <div className="h-full flex flex-col relative">
      {/* Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex gap-2">
        {['all', 'file', 'function', 'class'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors
              ${filter === f ? 'bg-accent/20 border-accent/40 text-accent' : 'border-border text-text-muted hover:text-text-secondary'}`}>
            {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1) + 's'}
          </button>
        ))}
      </div>

      {/* Stats */}
      {stats && (
        <div className="absolute top-3 right-3 z-10 glass-panel px-3 py-2 text-xs text-text-muted space-y-0.5">
          <div><span className="text-text-primary font-medium">{stats.total_nodes}</span> nodes</div>
          <div><span className="text-text-primary font-medium">{stats.total_edges}</span> edges</div>
        </div>
      )}

      {/* Graph */}
      <div className="flex-1 min-h-0">
        <ForceGraph2D
          ref={graphRef}
          graphData={filteredData}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.beginPath();
            ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          linkColor={(link) => EDGE_COLORS[link.type] || '#374151'}
          linkWidth={1}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          onNodeClick={handleNodeClick}
          backgroundColor="#0a0a0f"
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 z-10 glass-panel px-3 py-2 flex gap-4 text-xs">
        {Object.entries(TYPE_COLORS).filter(([k]) => k !== 'unknown').map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            <span className="text-text-muted capitalize">{type}</span>
          </div>
        ))}
        <span className="text-border">|</span>
        {Object.entries(EDGE_COLORS).filter(([k]) => k !== 'contains').map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 rounded" style={{ background: color }} />
            <span className="text-text-muted capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
