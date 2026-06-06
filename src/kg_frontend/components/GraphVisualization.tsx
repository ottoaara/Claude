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
      source: edge.source || edge.from,
      target: edge.target || edge.to,
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
      <div className="lg:col-span-2 bg-white/10 backdrop-blur-lg rounded-2xl overflow-hidden border border-white/20">
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
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-6 border border-white/20 h-[700px] overflow-y-auto">
        <h3 className="text-xl font-bold text-white mb-4">Node Details</h3>

        {selectedNode ? (
          <div className="space-y-4">
            <div>
              <p className="text-sm text-blue-200 mb-1">Type</p>
              <p className="text-lg font-semibold text-white">
                {selectedNode.type}
              </p>
            </div>

            <div>
              <p className="text-sm text-blue-200 mb-1">Name</p>
              <p className="text-lg font-semibold text-white">
                {selectedNode.label}
              </p>
            </div>

            <div className="border-t border-white/20 pt-4">
              <p className="text-sm text-blue-200 mb-2">Attributes</p>
              <div className="space-y-2">
                {Object.entries(selectedNode.data || {}).map(
                  ([key, value]) => {
                    // Skip internal properties
                    if (key.startsWith("_") || key === "id") return null;

                    return (
                      <div key={key} className="text-sm">
                        <span className="text-blue-300 font-medium">
                          {key}:{" "}
                        </span>
                        <span className="text-white">
                          {typeof value === "object"
                            ? JSON.stringify(value, null, 2)
                            : String(value)}
                        </span>
                      </div>
                    );
                  }
                )}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-gray-400 text-center mt-12">
            Click on a node to see details
          </p>
        )}
      </div>
    </div>
  );
}
