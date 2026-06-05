"use client";

export default function NodeDetail({
  node,
  rawGraph,
  api,
  onClose,
  onDone,
}: {
  node: any;
  rawGraph: any;
  api: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const neighbors = rawGraph?.relations?.filter(
    (r: any) => r.from === node.id || r.to === node.id
  ) ?? [];

  async function deleteNode() {
    await fetch(`${api}/entity/${encodeURIComponent(node.id)}`, { method: "DELETE" });
    onDone();
  }

  return (
    <div className="w-64 bg-gray-900 p-4 flex flex-col gap-3 overflow-y-auto shrink-0">
      <div className="flex justify-between items-start">
        <div>
          <p className="font-semibold text-white">{node.id}</p>
          <p className="text-xs text-gray-400">{node.type}</p>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">×</button>
      </div>

      {Object.keys(node.attributes ?? {}).length > 0 && (
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Attributes</p>
          {Object.entries(node.attributes).map(([k, v]: any) => (
            <div key={k} className="text-xs text-gray-300">
              <span className="text-gray-500">{k}:</span> {v}
            </div>
          ))}
        </div>
      )}

      {neighbors.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Relations</p>
          {neighbors.map((r: any, i: number) => (
            <div key={i} className="text-xs text-gray-300 py-0.5">
              {r.from === node.id
                ? <><span className="text-indigo-400">{r.from}</span> →[{r.relation}]→ <span className="text-emerald-400">{r.to}</span></>
                : <><span className="text-emerald-400">{r.from}</span> →[{r.relation}]→ <span className="text-indigo-400">{r.to}</span></>
              }
            </div>
          ))}
        </div>
      )}

      <button
        onClick={deleteNode}
        className="mt-auto rounded bg-red-900 py-1 text-xs font-medium text-red-300 hover:bg-red-700 transition-colors"
      >
        Delete entity
      </button>
    </div>
  );
}
