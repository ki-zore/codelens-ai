const API_BASE = '/api';

export const api = {
  // Ingestion
  async ingestGithub(repoUrl, branch = 'main') {
    const res = await fetch(`${API_BASE}/ingest/github`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: repoUrl, branch }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Ingestion failed');
    return res.json();
  },

  async ingestUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/ingest/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
    return res.json();
  },

  async getProjects() {
    const res = await fetch(`${API_BASE}/ingest/projects`);
    return res.json();
  },

  async getProject(id) {
    const res = await fetch(`${API_BASE}/ingest/projects/${id}`);
    return res.json();
  },

  async deleteProject(id) {
    const res = await fetch(`${API_BASE}/ingest/projects/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Delete failed with status ${res.status}`);
    }
    return res.json();
  },

  // Query
  async query(projectId, question, topK = 5) {
    const res = await fetch(`${API_BASE}/query/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, question, top_k: topK, include_graph: true }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Query failed');
    return res.json();
  },

  async queryStream(projectId, question, topK = 5, onChunk) {
    const res = await fetch(`${API_BASE}/query/stream`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, question, top_k: topK, include_graph: true }),
    });
    if (!res.ok) throw new Error('Stream failed');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.trim()) { try { onChunk(JSON.parse(line)); } catch {} }
      }
    }
    if (buffer.trim()) { try { onChunk(JSON.parse(buffer)); } catch {} }
  },

  // Graph
  async getGraph(projectId) {
    const res = await fetch(`${API_BASE}/graph/${projectId}`);
    return res.json();
  },

  async getGraphStats(projectId) {
    const res = await fetch(`${API_BASE}/graph/${projectId}/stats`);
    return res.json();
  },

  // Files
  async getFileTree(projectId) {
    const res = await fetch(`${API_BASE}/files/${projectId}/tree`);
    return res.json();
  },

  async getFileContent(projectId, filePath) {
    const res = await fetch(`${API_BASE}/files/${projectId}/content/${filePath}`);
    return res.json();
  },
};
