"use client";

import { useEffect, useState, useRef } from "react";
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

export default function GraphVisualization({ companyName }: Props) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
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

  // Transform data for react-force-graph
  const transformedData = {
    nodes: graphData.nodes.map((node) => ({
      id: node.id,
      name: node.label,
      type: node.type,
      data: node.data,
      val: node.type === "Company" ? 20 : 10,
    })),
    links: graphData.edges.map((edge) => ({
      source: edge.source || (edge as any).from,
      target: edge.target || (edge as any).to,
      label: edge.type,
      data: edge.data,
    })),
  };

  const getNodeColor = (node: any) => {
    const colors: Record<string, string> = {
      Company: "#3b82f6", // blue
      Financial: "#10b981", // green
      News: "#ef4444", // red
      Product: "#8b5cf6", // purple
      Industry: "#f59e0b", // amber
      default: "#6b7280", // gray
    };
    return colors[node.type] || colors.default;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Graph Visualization */}
      <div className="lg:col-span-2 bg-slate-900 rounded-2xl overflow-hidden border-2 border-gray-700 shadow-md">
        <div className="h-[700px] relative">
          <ForceGraph2D
            ref={graphRef}
            graphData={transformedData}
            nodeLabel="name"
            nodeColor={getNodeColor}
            nodeRelSize={6}
            linkLabel="label"
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.2}
            onNodeClick={(node: any) => {
              const originalNode = graphData.nodes.find(
                (n) => n.id === node.id
              );
              setSelectedNode(originalNode || null);
            }}
            backgroundColor="rgba(15, 23, 42, 0.5)"
            linkColor={() => "#94a3b8"}
            nodeCanvasObject={(node: any, ctx: any, globalScale: number) => {
              const label = node.name;
              const fontSize = 12 / globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;

              // Draw node circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
              ctx.fillStyle = getNodeColor(node);
              ctx.fill();
              ctx.strokeStyle = "#fff";
              ctx.lineWidth = 0.5;
              ctx.stroke();

              // Draw label
              ctx.textAlign = "center";
              ctx.textBaseline = "middle";
              ctx.fillStyle = "#fff";
              ctx.fillText(label, node.x, node.y + node.val + fontSize);
            }}
          />
        </div>

        {/* Legend */}
        <div className="p-4 bg-slate-900/50 border-t border-white/10">
          <p className="text-xs text-blue-200 mb-2 font-semibold">Legend:</p>
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-white">Company</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-white">Financials</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-white">News</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-purple-500"></div>
              <span className="text-white">Products</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-500"></div>
              <span className="text-white">Industry</span>
            </div>
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
            {/* Type badge */}
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ background: getNodeColor(selectedNode) }} />
              <span className="text-xs font-bold uppercase tracking-wide px-2 py-0.5 rounded"
                style={{ background: getNodeColor(selectedNode) + "22", color: getNodeColor(selectedNode) }}>
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
