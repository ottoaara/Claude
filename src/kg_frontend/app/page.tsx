"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import AddEntityForm from "@/components/AddEntityForm";
import AddRelationForm from "@/components/AddRelationForm";
import NodeDetail from "@/components/NodeDetail";
import CytoscapeComponent from "react-cytoscapejs";
import type cytoscape from "cytoscape";

const API = "http://localhost:8000";

const TYPE_COLORS: Record<string, string> = {
  person: "#6366f1",
  project: "#10b981",
  service: "#f59e0b",
  component: "#ef4444",
  concept: "#8b5cf6",
};

function colorFor(type: string) {
  return TYPE_COLORS[type] ?? "#94a3b8";
}

const stylesheet: cytoscape.Stylesheet[] = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      "label": "data(label)",
      "color": "#ffffff",
      "font-size": "13px",
      "font-weight": "500",
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 6,
      "width": 36,
      "height": 36,
      "border-width": 2,
      "border-color": "rgba(255,255,255,0.15)",
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-width": 3,
      "border-color": "#ffffff",
    },
  },
  {
    selector: "edge",
    style: {
      "width": 2,
      "line-color": "#475569",
      "target-arrow-color": "#475569",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "label": "data(label)",
      "font-size": "11px",
      "color": "#94a3b8",
      "text-background-color": "#030712",
      "text-background-opacity": 0.8,
      "text-background-padding": "3px",
    },
  },
];

const layout = {
  name: "cose",
  animate: true,
  animationDuration: 500,
  nodeRepulsion: () => 8000,
  idealEdgeLength: () => 150,
  edgeElasticity: () => 100,
  gravity: 0.4,
  randomize: false,
  padding: 60,
};

export default function Home() {
  const [elements, setElements] = useState<cytoscape.ElementDefinition[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [rawGraph, setRawGraph] = useState<any>(null);
  const [entityNames, setEntityNames] = useState<string[]>([]);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const fetchGraph = useCallback(async () => {
    const res = await fetch(`${API}/graph`);
    const data = await res.json();
    setRawGraph(data);
    setEntityNames(Object.keys(data.entities));

    const nodes: cytoscape.ElementDefinition[] = Object.entries(data.entities).map(
      ([id, val]: any) => ({
        data: { id, label: id, color: colorFor(val.type), type: val.type, attributes: val.attributes },
      })
    );
    const edges: cytoscape.ElementDefinition[] = data.relations.map((r: any, i: number) => ({
      data: { id: `e${i}`, source: r.from, target: r.to, label: r.relation },
    }));
    setElements([...nodes, ...edges]);
  }, []);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  useEffect(() => {
    if (!cyRef.current || elements.length === 0) return;
    const cy = cyRef.current;
    cy.layout(layout).run();
  }, [elements]);

  function handleCyReady(cy: cytoscape.Core) {
    cyRef.current = cy;
    cy.on("tap", "node", evt => {
      const node = evt.target;
      setSelected({
        id: node.data("id"),
        type: node.data("type"),
        attributes: node.data("attributes") ?? {},
        color: node.data("color"),
      });
    });
    cy.on("tap", evt => {
      if (evt.target === cy) setSelected(null);
    });
  }

  return (
    <div className="flex h-screen bg-gray-950 text-white">
      {/* Left sidebar */}
      <div className="w-72 flex flex-col gap-4 p-4 bg-gray-900 overflow-y-auto shrink-0">
        <h1 className="text-lg font-bold text-indigo-400">Knowledge Graph</h1>
        <AddEntityForm api={API} onDone={fetchGraph} />
        <AddRelationForm api={API} entities={entityNames} onDone={fetchGraph} />
        <div className="mt-2">
          <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Types</p>
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2 text-xs py-0.5">
              <span className="w-3 h-3 rounded-full inline-block" style={{ background: color }} />
              {type}
            </div>
          ))}
        </div>
      </div>

      {/* Graph canvas */}
      <div className="flex-1 relative overflow-hidden">
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          cy={handleCyReady}
          style={{ width: "100%", height: "100%" }}
          layout={{ name: "preset" }}
        />
      </div>

      {/* Right detail panel */}
      {selected && (
        <NodeDetail
          node={selected}
          rawGraph={rawGraph}
          api={API}
          onClose={() => setSelected(null)}
          onDone={() => { fetchGraph(); setSelected(null); }}
        />
      )}
    </div>
  );
}
