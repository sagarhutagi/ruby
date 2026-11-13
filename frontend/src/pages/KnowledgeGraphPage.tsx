import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Connection,
  Edge,
  Node,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Network,
  Plus,
  Filter,
  Download,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FolderDown,
  Sparkles,
  Link,
  X,
  Layers,
} from 'lucide-react';
import {
  fetchGraph,
  createGraphNode,
  updateGraphNode,
  deleteGraphNode,
  createGraphEdge,
  fetchPrerequisites,
  extractGraphFromDocument,
  previewObsidianExport,
  exportToObsidianVault,
  getObsidianZipUrl,
  KnowledgeNodeItem,
  PrerequisiteChainResult,
  ObsidianPreviewResult,
  ObsidianExportResult,
  fetchDocuments,
} from '../services/api';

// Custom node styling helper
const getNodeColor = (type: string) => {
  switch (type) {
    case 'subject':
      return { bg: 'bg-purple-950/80', border: 'border-purple-500', text: 'text-purple-300' };
    case 'topic':
      return { bg: 'bg-cyan-950/80', border: 'border-cyan-500', text: 'text-cyan-300' };
    case 'formula':
      return { bg: 'bg-amber-950/80', border: 'border-amber-500', text: 'text-amber-300' };
    case 'document':
      return { bg: 'bg-emerald-950/80', border: 'border-emerald-500', text: 'text-emerald-300' };
    case 'concept':
    default:
      return { bg: 'bg-indigo-950/80', border: 'border-indigo-500', text: 'text-indigo-300' };
  }
};

export const KnowledgeGraphPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [selectedNodeType, setSelectedNodeType] = useState<string>('');
  const [verifiedOnly, setVerifiedOnly] = useState<boolean>(false);

  // Inspector & Modals
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showAddNodeModal, setShowAddNodeModal] = useState<boolean>(false);
  const [showAddEdgeModal, setShowAddEdgeModal] = useState<boolean>(false);
  const [showExtractModal, setShowExtractModal] = useState<boolean>(false);
  const [showObsidianModal, setShowObsidianModal] = useState<boolean>(false);
  const [prereqChain, setPrereqChain] = useState<PrerequisiteChainResult | null>(null);

  // Form states
  const [newNodeLabel, setNewNodeLabel] = useState('');
  const [newNodeType, setNewNodeType] = useState('concept');
  const [newNodeDesc, setNewNodeDesc] = useState('');
  const [edgeSourceId, setEdgeSourceId] = useState('');
  const [edgeTargetId, setEdgeTargetId] = useState('');
  const [edgeRelation, setEdgeRelation] = useState('RELATED_TO');
  const [extractDocId, setExtractDocId] = useState('');

  // Obsidian Export state
  const [obsidianPath, setObsidianPath] = useState('./data/obsidian_vault');
  const [allowOverwrite, setAllowOverwrite] = useState(false);
  const [previewResult, setPreviewResult] = useState<ObsidianPreviewResult | null>(null);
  const [exportResult, setExportResult] = useState<ObsidianExportResult | null>(null);

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Fetch subjects
  const { data: subjects = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['subjects'],
    queryFn: async () => {
      const res = await fetch('/api/v1/subjects');
      if (!res.ok) return [];
      return res.json();
    },
  });

  // Fetch documents for extraction
  const { data: documents = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: () => fetchDocuments(),
  });

  // Fetch Graph Data
  const { data: graphData, isLoading: loadingGraph } = useQuery({
    queryKey: ['knowledgeGraph', selectedSubjectId, selectedNodeType, verifiedOnly],
    queryFn: () =>
      fetchGraph(
        selectedSubjectId || undefined,
        selectedNodeType || undefined,
        verifiedOnly
      ),
  });

  // Sync ReactFlow nodes & edges with query data
  React.useEffect(() => {
    if (!graphData) return;

    const rfNodes: Node[] = graphData.nodes.map((n, idx) => {
      const colors = getNodeColor(n.node_type);
      const isUnverified = !n.is_verified;

      // Layout fallback if positions are default 0
      const x = n.position_x !== 0 ? n.position_x : 100 + (idx % 6) * 190;
      const y = n.position_y !== 0 ? n.position_y : 80 + Math.floor(idx / 6) * 140;

      return {
        id: n.id,
        position: { x, y },
        data: {
          label: (
            <div
              className={`px-3 py-2 rounded-xl border transition-all ${colors.bg} ${colors.border} ${
                isUnverified ? 'border-dashed ring-1 ring-amber-500/40' : 'shadow-md'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className={`text-[9px] uppercase font-bold tracking-wider ${colors.text}`}>
                  {n.node_type}
                </span>
                {isUnverified && (
                  <span className="px-1 py-0.2 rounded text-[8px] bg-amber-500/20 text-amber-300 font-medium">
                    AI Suggested
                  </span>
                )}
              </div>
              <div className="text-xs font-semibold text-zinc-100 max-w-[150px] truncate">
                {n.label}
              </div>
            </div>
          ),
          raw: n,
        },
      };
    });

    const rfEdges: Edge[] = graphData.edges.map((e) => {
      const isPrereq = e.relationship_type === 'PREREQUISITE_OF';
      return {
        id: e.id,
        source: e.source_id,
        target: e.target_id,
        label: e.relationship_type.replace('_', ' ').toLowerCase(),
        animated: isPrereq,
        markerEnd: { type: MarkerType.ArrowClosed, color: isPrereq ? '#6366f1' : '#71717a' },
        style: {
          stroke: isPrereq ? '#6366f1' : '#71717a',
          strokeDasharray: e.is_verified ? undefined : '4 4',
        },
        labelStyle: { fill: '#a1a1aa', fontSize: 10, fontWeight: 500 },
      };
    });

    setNodes(rfNodes);
    setEdges(rfEdges);
  }, [graphData, setNodes, setEdges]);

  // Mutations
  const createNodeMutation = useMutation({
    mutationFn: createGraphNode,
    onSuccess: (node) => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeGraph'] });
      setShowAddNodeModal(false);
      setNewNodeLabel('');
      setNewNodeDesc('');
      setSelectedNodeId(node.id);
    },
  });

  const updateNodeMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<KnowledgeNodeItem> }) =>
      updateGraphNode(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeGraph'] });
    },
  });

  const deleteNodeMutation = useMutation({
    mutationFn: deleteGraphNode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeGraph'] });
      setSelectedNodeId(null);
    },
  });

  const createEdgeMutation = useMutation({
    mutationFn: createGraphEdge,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeGraph'] });
      setShowAddEdgeModal(false);
    },
    onError: (err: any) => alert(err.message),
  });

  const extractMutation = useMutation({
    mutationFn: extractGraphFromDocument,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['knowledgeGraph'] });
      setShowExtractModal(false);
      alert(`Extracted ${data.nodes_created} concepts and ${data.edges_created} relationships!`);
    },
    onError: (err: any) => alert(err.message),
  });

  const previewObsidianMutation = useMutation({
    mutationFn: () => previewObsidianExport(obsidianPath, selectedSubjectId || undefined),
    onSuccess: (res) => setPreviewResult(res),
  });

  const exportObsidianMutation = useMutation({
    mutationFn: () =>
      exportToObsidianVault(obsidianPath, selectedSubjectId || undefined, allowOverwrite),
    onSuccess: (res) => setExportResult(res),
  });

  const handleConnect = useCallback(
    (params: Connection) => {
      if (params.source && params.target) {
        createEdgeMutation.mutate({
          source_id: params.source,
          target_id: params.target,
          relationship_type: 'RELATED_TO',
        });
      }
    },
    [createEdgeMutation]
  );

  const selectedNode = useMemo(() => {
    if (!graphData || !selectedNodeId) return null;
    return graphData.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [graphData, selectedNodeId]);

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
    setPrereqChain(null);
  };

  const handleFetchPrereqs = async (nodeId: string) => {
    try {
      const res = await fetchPrerequisites(nodeId);
      setPrereqChain(res);
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="h-[calc(100vh-5rem)] flex flex-col space-y-3">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-zinc-800 pb-3">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <Network className="w-5 h-5 text-indigo-400" />
            Academic Knowledge Graph & Vault Explorer
          </h2>
          <p className="text-xs text-zinc-400">
            Interactive multi-subject concept topology, prerequisite learning paths, and Obsidian Markdown exporter.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddNodeModal(true)}
            className="flex items-center gap-1 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5 text-indigo-400" />
            Add Concept
          </button>
          <button
            onClick={() => setShowAddEdgeModal(true)}
            className="flex items-center gap-1 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition-colors"
          >
            <Link className="w-3.5 h-3.5 text-cyan-400" />
            Connect
          </button>
          <button
            onClick={() => setShowExtractModal(true)}
            className="flex items-center gap-1 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            Auto-Extract
          </button>
          <button
            onClick={() => {
              setShowObsidianModal(true);
              setPreviewResult(null);
              setExportResult(null);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg shadow-md transition-colors"
          >
            <FolderDown className="w-3.5 h-3.5" />
            Obsidian Vault
          </button>
        </div>
      </div>

      {/* Filter and stats row */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-zinc-900/60 p-2.5 rounded-xl border border-zinc-800/80 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-zinc-400" />
          {/* Subject Filter */}
          <select
            value={selectedSubjectId}
            onChange={(e) => setSelectedSubjectId(e.target.value)}
            className="px-2.5 py-1 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200"
          >
            <option value="">All Subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          {/* Node Type Filter */}
          <select
            value={selectedNodeType}
            onChange={(e) => setSelectedNodeType(e.target.value)}
            className="px-2.5 py-1 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200"
          >
            <option value="">All Types</option>
            <option value="concept">Concepts</option>
            <option value="topic">Topics</option>
            <option value="formula">Formulas</option>
            <option value="document">Documents</option>
            <option value="subject">Subjects</option>
          </select>

          {/* Verified Only */}
          <label className="flex items-center gap-1.5 text-zinc-400 cursor-pointer pl-1">
            <input
              type="checkbox"
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
              className="rounded bg-zinc-950 border-zinc-700 text-indigo-600"
            />
            <span>Verified only</span>
          </label>
        </div>

        <div className="flex items-center gap-4 text-zinc-400 text-[11px]">
          <span>
            Nodes: <strong className="text-zinc-200">{nodes.length}</strong>
          </span>
          <span>
            Edges: <strong className="text-zinc-200">{edges.length}</strong>
          </span>
        </div>
      </div>

      {/* Main Graph Area and Side Inspector */}
      <div className="flex-1 rounded-2xl bg-zinc-950 border border-zinc-800/90 relative overflow-hidden flex">
        {loadingGraph ? (
          <div className="w-full h-full flex items-center justify-center text-xs text-zinc-500">
            Loading Knowledge Graph...
          </div>
        ) : (
          <div className="flex-1 h-full">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={handleConnect}
              onNodeClick={handleNodeClick}
              fitView
            >
              <Background color="#27272a" gap={18} size={1} />
              <Controls className="bg-zinc-900 border border-zinc-800 fill-zinc-400" />
              <MiniMap
                nodeColor="#6366f1"
                maskColor="rgba(9, 9, 11, 0.7)"
                className="bg-zinc-900 border border-zinc-800 rounded-xl"
              />
            </ReactFlow>
          </div>
        )}

        {/* Selected Node Inspector Drawer */}
        {selectedNode && (
          <div className="w-80 border-l border-zinc-800 bg-zinc-900/90 p-4 flex flex-col justify-between overflow-y-auto z-10 shadow-2xl backdrop-blur-md">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <span
                    className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                      getNodeColor(selectedNode.node_type).bg
                    } ${getNodeColor(selectedNode.node_type).text}`}
                  >
                    {selectedNode.node_type}
                  </span>
                  <h3 className="text-sm font-bold text-zinc-100 mt-1">{selectedNode.label}</h3>
                </div>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="p-1 text-zinc-500 hover:text-zinc-300"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Status and Verification Badge */}
              <div className="flex items-center justify-between p-2.5 rounded-xl bg-zinc-950 border border-zinc-800 text-xs">
                <span className="text-zinc-400">Verification:</span>
                <button
                  onClick={() =>
                    updateNodeMutation.mutate({
                      id: selectedNode.id,
                      data: { is_verified: !selectedNode.is_verified },
                    })
                  }
                  className={`flex items-center gap-1 font-semibold text-xs ${
                    selectedNode.is_verified ? 'text-emerald-400' : 'text-amber-400'
                  }`}
                >
                  {selectedNode.is_verified ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Verified
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Unverified AI
                    </>
                  )}
                </button>
              </div>

              {/* Description */}
              <div className="space-y-1">
                <label className="text-[10px] text-zinc-400 uppercase font-semibold">Overview</label>
                <textarea
                  rows={3}
                  value={selectedNode.description || ''}
                  onChange={(e) =>
                    updateNodeMutation.mutate({
                      id: selectedNode.id,
                      data: { description: e.target.value },
                    })
                  }
                  placeholder="Add academic concept description or formula notes..."
                  className="w-full p-2.5 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Prerequisite Action */}
              <div className="pt-2">
                <button
                  onClick={() => handleFetchPrereqs(selectedNode.id)}
                  className="w-full flex items-center justify-center gap-1.5 py-2 bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 text-xs font-semibold rounded-lg border border-indigo-800/60 transition-colors"
                >
                  <Layers className="w-3.5 h-3.5" />
                  View Prerequisite Path
                </button>
              </div>

              {/* Prerequisite Chain Result */}
              {prereqChain && (
                <div className="p-3 bg-zinc-950 rounded-xl border border-indigo-900/40 space-y-2 text-xs">
                  <div className="font-semibold text-indigo-300">
                    Required Knowledge ({prereqChain.prerequisites_count}):
                  </div>
                  {prereqChain.study_order.length === 0 ? (
                    <div className="text-[11px] text-zinc-500">
                      No prerequisites required for this foundational concept.
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {prereqChain.study_order.map((step, idx) => (
                        <div key={step.id} className="flex items-center gap-2 text-zinc-200 text-xs">
                          <span className="w-4 h-4 rounded-full bg-indigo-600/30 text-indigo-400 flex items-center justify-center text-[10px] font-bold">
                            {idx + 1}
                          </span>
                          <span>{step.label}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Delete button */}
            <div className="pt-4 border-t border-zinc-800">
              <button
                onClick={() => {
                  if (confirm(`Delete node "${selectedNode.label}"?`)) {
                    deleteNodeMutation.mutate(selectedNode.id);
                  }
                }}
                className="w-full flex items-center justify-center gap-1.5 py-2 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 rounded-lg transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete Node
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ==================== ADD NODE MODAL ==================== */}
      {showAddNodeModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!newNodeLabel.trim()) return;
              createNodeMutation.mutate({
                label: newNodeLabel.trim(),
                node_type: newNodeType,
                description: newNodeDesc.trim() || undefined,
                subject_id: selectedSubjectId || undefined,
              });
            }}
            className="w-full max-w-md p-5 bg-zinc-900 rounded-2xl border border-zinc-800 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
              <h3 className="text-sm font-semibold text-zinc-100">Add Academic Concept Node</h3>
              <button
                type="button"
                onClick={() => setShowAddNodeModal(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Concept Name / Label</label>
                <input
                  type="text"
                  value={newNodeLabel}
                  onChange={(e) => setNewNodeLabel(e.target.value)}
                  placeholder="e.g., QuickSort or Amdahl's Law"
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-100 focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Node Type</label>
                <select
                  value={newNodeType}
                  onChange={(e) => setNewNodeType(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-100"
                >
                  <option value="concept">Concept</option>
                  <option value="topic">Topic</option>
                  <option value="formula">Formula / Theorem</option>
                  <option value="subject">Subject</option>
                  <option value="document">Document</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Description / Notes</label>
                <textarea
                  rows={3}
                  value={newNodeDesc}
                  onChange={(e) => setNewNodeDesc(e.target.value)}
                  placeholder="Pedagogical summary of this concept..."
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-100"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAddNodeModal(false)}
                className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createNodeMutation.isPending || !newNodeLabel.trim()}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                {createNodeMutation.isPending ? 'Adding...' : 'Create Node'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ==================== ADD EDGE MODAL ==================== */}
      {showAddEdgeModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (!edgeSourceId || !edgeTargetId || edgeSourceId === edgeTargetId) return;
              createEdgeMutation.mutate({
                source_id: edgeSourceId,
                target_id: edgeTargetId,
                relationship_type: edgeRelation,
              });
            }}
            className="w-full max-w-md p-5 bg-zinc-900 rounded-2xl border border-zinc-800 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
              <h3 className="text-sm font-semibold text-zinc-100">Connect Concepts with Relationship</h3>
              <button
                type="button"
                onClick={() => setShowAddEdgeModal(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Source Concept (From)</label>
                <select
                  value={edgeSourceId}
                  onChange={(e) => setEdgeSourceId(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-100"
                  required
                >
                  <option value="">Select source node</option>
                  {graphData?.nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.label} ({n.node_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Relationship Type</label>
                <select
                  value={edgeRelation}
                  onChange={(e) => setEdgeRelation(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-100"
                >
                  <option value="PREREQUISITE_OF">PREREQUISITE_OF (Must learn A before B)</option>
                  <option value="RELATED_TO">RELATED_TO (Conceptually connected)</option>
                  <option value="PART_OF">PART_OF (Sub-component / section)</option>
                  <option value="EXPLAINED_IN">EXPLAINED_IN (Derived from source)</option>
                  <option value="CONTRADICTS">CONTRADICTS (Opposing paradigm)</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Target Concept (To)</label>
                <select
                  value={edgeTargetId}
                  onChange={(e) => setEdgeTargetId(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-100"
                  required
                >
                  <option value="">Select target node</option>
                  {graphData?.nodes
                    .filter((n) => n.id !== edgeSourceId)
                    .map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.label} ({n.node_type})
                      </option>
                    ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowAddEdgeModal(false)}
                className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createEdgeMutation.isPending || !edgeSourceId || !edgeTargetId}
                className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                {createEdgeMutation.isPending ? 'Connecting...' : 'Create Connection'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ==================== AUTO EXTRACT MODAL ==================== */}
      {showExtractModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-md p-5 bg-zinc-900 rounded-2xl border border-zinc-800 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-zinc-800">
              <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                Extract Concepts from Document
              </h3>
              <button onClick={() => setShowExtractModal(false)} className="text-zinc-500 hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-zinc-400">
              Select an ingested library document. Headings, defined terms, and LaTeX formulas will be extracted into the graph as AI suggestions.
            </p>

            <div className="space-y-3 text-xs">
              <select
                value={extractDocId}
                onChange={(e) => setExtractDocId(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-zinc-100"
              >
                <option value="">Select a document</option>
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title} ({d.file_type})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowExtractModal(false)}
                className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => extractMutation.mutate(extractDocId)}
                disabled={extractMutation.isPending || !extractDocId}
                className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-lg disabled:opacity-50"
              >
                {extractMutation.isPending ? 'Extracting...' : 'Extract Concepts'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== OBSIDIAN EXPORT MODAL ==================== */}
      {showObsidianModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="w-full max-w-lg p-6 bg-zinc-900 rounded-2xl border border-zinc-800 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <FolderDown className="w-4 h-4 text-indigo-400" />
                Obsidian Vault Markdown Exporter
              </h3>
              <button onClick={() => setShowObsidianModal(false)} className="text-zinc-500 hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Option 1: One-Click ZIP Download */}
              <div className="p-4 rounded-xl bg-zinc-950 border border-indigo-900/40 space-y-2">
                <div className="font-semibold text-indigo-300 flex items-center justify-between">
                  <span>Direct ZIP Archive Download</span>
                  <a
                    href={getObsidianZipUrl(selectedSubjectId || undefined)}
                    download="ruby_obsidian_vault.zip"
                    className="flex items-center gap-1.5 px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download ZIP
                  </a>
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Downloads a complete Obsidian vault package with YAML frontmatter, [[wikilinks]], tags, and a master index note ready to open in Obsidian.
                </p>
              </div>

              {/* Option 2: Sync to Local Vault Path */}
              <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-3">
                <div className="font-semibold text-zinc-200">Sync to Local Directory</div>
                <div className="space-y-1">
                  <label className="text-[11px] text-zinc-400">Vault Directory Path</label>
                  <input
                    type="text"
                    value={obsidianPath}
                    onChange={(e) => setObsidianPath(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg font-mono text-zinc-200"
                  />
                </div>

                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 text-zinc-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={allowOverwrite}
                      onChange={(e) => setAllowOverwrite(e.target.checked)}
                      className="rounded bg-zinc-900 border-zinc-700 text-indigo-600"
                    />
                    <span>Allow overwrite of existing files</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => previewObsidianMutation.mutate()}
                    disabled={previewObsidianMutation.isPending}
                    className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg border border-zinc-700 font-medium"
                  >
                    {previewObsidianMutation.isPending ? 'Checking...' : 'Preview Conflicts'}
                  </button>
                </div>

                {previewResult && (
                  <div className="p-3 bg-zinc-900/80 rounded-lg border border-zinc-800 space-y-1.5 text-[11px]">
                    <div className="text-zinc-300 font-medium">Preview Summary:</div>
                    <div>Files to Create: <strong className="text-emerald-400">{previewResult.files_to_create.length}</strong></div>
                    <div>Files to Overwrite: <strong className={previewResult.files_to_overwrite.length > 0 ? 'text-amber-400' : 'text-zinc-400'}>{previewResult.files_to_overwrite.length}</strong></div>
                    {previewResult.has_conflicts && !allowOverwrite && (
                      <div className="text-amber-400 font-medium pt-1">
                        ⚠️ Existing files will be protected unless "Allow overwrite" is enabled.
                      </div>
                    )}
                  </div>
                )}

                {exportResult && (
                  <div className="p-3 bg-emerald-950/30 rounded-lg border border-emerald-900/50 text-[11px] text-emerald-300">
                    ✓ Successfully exported {exportResult.written_count} notes to <code>{exportResult.vault_path}</code>
                    {exportResult.skipped_count > 0 && ` (${exportResult.skipped_count} skipped)`}
                  </div>
                )}

                <div className="pt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={() => exportObsidianMutation.mutate()}
                    disabled={exportObsidianMutation.isPending}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg shadow disabled:opacity-50"
                  >
                    {exportObsidianMutation.isPending ? 'Writing Notes...' : 'Export to Vault'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraphPage;
