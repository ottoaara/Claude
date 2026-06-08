"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import { api, APIError } from "../lib/api";

// Dynamically import react-force-graph to avoid SSR issues
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

interface Node {
  id: string;
  label: string;
  type: string;
  data: any;
}

interface Edge {
  source: string;
  target: string;
  type: string;
  data?: any;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

interface Props {
  companyName: string;
}

// ─── Node type config ─────────────────────────────────────────────────────────
const NODE_TYPES: Record<string, { color: string; label: string }> = {
  Company:     { color: "#3b82f6", label: "Company" },
  Financial:   { color: "#10b981", label: "Financials" },
  News:        { color: "#ef4444", label: "News" },
  Product:     { color: "#8b5cf6", label: "Products" },
  Industry:    { color: "#f59e0b", label: "Industry" },
  PeerCompany: { color: "#06b6d4", label: "Peer Company" },
  Officer:     { color: "#ec4899", label: "Officer" },
};

const getNodeColor = (type: string) =>
  NODE_TYPES[type]?.color ?? "#6b7280";

export default function GraphVisualization({ companyName }: Props) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());
  const graphRef = useRef<any>();

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        setLoading(true);
        const data = await api.getVisualizationData(companyName);
        setGraphData(data);
      } catch (err) {
        if (err instanceof APIError) {
          setError(err.message);
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchGraphData();
  }, [companyName]);

  const toggleType = useCallback((type: string) => {
    setHiddenTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      // deselect node if its type is now hidden
      setSelectedNode(sel => (sel?.type === type ? null : sel));
      return next;
    });
  }, []);

  if (loading) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-12 text-center border border-white/20">
        <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-white">Loading knowledge graph...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/20 border border-red-500/50 rounded-2xl p-8 text-red-200">
        <p className="font-semibold mb-2">Error loading graph:</p>
        <p>{error}</p>
      </div>
    );
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 text-center border border-white/20">
        <p className="text-white">No graph data available</p>
      </div>
    );
  }

  // Which node types actually exist in this graph?
  const presentTypes = [...new Set(graphData.nodes.map(n => n.type))];

  // Filter nodes + edges by hidden types
  const visibleNodes = graphData.nodes.filter(n => !hiddenTypes.has(n.type));
  const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
  const visibleEdges = graphData.edges.filter(
    e => visibleNodeIds.has(e.source as string) && visibleNodeIds.has(e.target as string)
  );

  // Key changes whenever hidden types change, forcing ForceGraph2D to remount.
  // react-force-graph-2d mutates node objects in-place (adds x/y/vx/vy), so we
  // deep-copy the filtered data on each render so the filter always starts clean.
  const filterKey = [...hiddenTypes].sort().join(",") || "all";

  const graphDataForRender = {
    nodes: visibleNodes.map((node) => ({
      id: node.id,
      name: node.label,
      type: node.type,
      data: node.data,
      val: node.type === "Company" ? 20 : 10,
    })),
    links: visibleEdges.map((edge) => ({
      source: edge.source || (edge as any).from,
      target: edge.target || (edge as any).to,
      label: edge.type,
      data: edge.data,
    })),
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Graph Visualization */}
      <div className="lg:col-span-2 bg-slate-900 rounded-2xl overflow-hidden border-2 border-gray-700 shadow-md">
        <div className="h-[700px] relative">
          <ForceGraph2D
            key={filterKey}
            ref={graphRef}
            graphData={graphDataForRender}
            nodeLabel="name"
            nodeColor={(n: any) => getNodeColor(n.type)}
            nodeRelSize={6}
            linkLabel="label"
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.2}
            onNodeClick={(node: any) => {
              const originalNode = graphData.nodes.find(n => n.id === node.id);
              setSelectedNode(originalNode || null);
            }}
            backgroundColor="rgba(15, 23, 42, 0.5)"
            linkColor={() => "#94a3b8"}
            nodeCanvasObject={(node: any, ctx: any, globalScale: number) => {
              const label = node.name;
              const fontSize = 12 / globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              ctx.beginPath();
              ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
              ctx.fillStyle = getNodeColor(node.type);
              ctx.fill();
              ctx.strokeStyle = "#fff";
              ctx.lineWidth = 0.5;
              ctx.stroke();
              ctx.textAlign = "center";
              ctx.textBaseline = "middle";
              ctx.fillStyle = "#fff";
              ctx.fillText(label, node.x, node.y + node.val + fontSize);
            }}
          />
        </div>

        {/* Filterable Legend */}
        <div className="p-4 bg-slate-900/80 border-t border-white/10">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-blue-200 font-semibold uppercase tracking-wide">
              Dimensions — click to filter
            </p>
            {hiddenTypes.size > 0 && (
              <button
                onClick={() => setHiddenTypes(new Set())}
                className="text-xs text-blue-300 hover:text-white underline"
              >
                Show all
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            {presentTypes.map(type => {
              const cfg = NODE_TYPES[type] ?? { color: "#6b7280", label: type };
              const hidden = hiddenTypes.has(type);
              const count = graphData.nodes.filter(n => n.type === type).length;
              return (
                <button
                  key={type}
                  onClick={() => toggleType(type)}
                  title={hidden ? `Show ${cfg.label}` : `Hide ${cfg.label}`}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold transition-all select-none ${
                    hidden
                      ? "border-white/20 bg-white/5 text-white/30 line-through"
                      : "border-white/30 bg-white/10 text-white hover:bg-white/20"
                  }`}
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ background: hidden ? "#555" : cfg.color }}
                  />
                  {cfg.label}
                  <span className={`ml-0.5 ${hidden ? "text-white/20" : "text-white/50"}`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Node Details Panel */}
      <div className="bg-white rounded-2xl border-2 border-gray-200 shadow-md p-5 h-[700px] overflow-y-auto">
        <h3 className="text-xl font-bold text-[#D71E28] mb-4 border-b-4 border-[#D71E28] pb-3 uppercase tracking-wide">
          Node Details
        </h3>

        {selectedNode ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ background: getNodeColor(selectedNode.type) }} />
              <span className="text-xs font-bold uppercase tracking-wide px-2 py-0.5 rounded"
                style={{ background: getNodeColor(selectedNode.type) + "22", color: getNodeColor(selectedNode.type) }}>
                {selectedNode.type}
              </span>
            </div>

            <div>
              <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-1">Name</p>
              <p className="text-base font-semibold text-[#333333]">{selectedNode.label}</p>
            </div>

            <div className="border-t-2 border-gray-100 pt-3 space-y-2">
              <p className="text-xs text-[#666666] font-bold uppercase tracking-wide mb-2">Properties</p>
              {Object.entries(selectedNode.data || {}).map(([key, value]) => {
                if (!value && value !== 0 && value !== false) return null;
                if (key === "id" || key === "timestamp") return null;

                let display: string;
                if (Array.isArray(value)) {
                  display = value.length ? value.join(", ") : "—";
                } else if (typeof value === "object") {
                  display = JSON.stringify(value);
                } else {
                  display = String(value);
                }
                if (display.length > 300) display = display.slice(0, 297) + "…";

                return (
                  <div key={key} className="text-sm border-b border-gray-50 pb-1">
                    <span className="text-[#666666] font-semibold capitalize">
                      {key.replace(/_/g, " ")}:{" "}
                    </span>
                    <span className="text-[#333333]">{display}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="text-center mt-16">
            <div className="text-4xl mb-3">🔍</div>
            <p className="text-[#666666] font-semibold">Click a node to inspect</p>
            <p className="text-xs text-gray-400 mt-1">Company, Financial, News, Product nodes all carry detail</p>
          </div>
        )}
      </div>
    </div>
  );
}
