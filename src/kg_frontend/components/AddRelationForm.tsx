"use client";

import { useState } from "react";

export default function AddRelationForm({
  api,
  entities,
  onDone,
}: {
  api: string;
  entities: string[];
  onDone: () => void;
}) {
  const [from, setFrom] = useState("");
  const [relation, setRelation] = useState("");
  const [to, setTo] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const res = await fetch(`${api}/relation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_entity: from, relation, to_entity: to }),
    });
    if (!res.ok) {
      const data = await res.json();
      setError(data.detail ?? "Error");
      return;
    }
    setRelation("");
    onDone();
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2">
      <p className="text-xs text-gray-400 uppercase tracking-wide">Add Relation</p>
      <select
        className="rounded bg-gray-800 px-2 py-1 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
        value={from}
        onChange={e => setFrom(e.target.value)}
        required
      >
        <option value="">From…</option>
        {entities.map(e => <option key={e}>{e}</option>)}
      </select>
      <input
        className="rounded bg-gray-800 px-2 py-1 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
        placeholder="Relation (e.g. uses)"
        value={relation}
        onChange={e => setRelation(e.target.value)}
        required
      />
      <select
        className="rounded bg-gray-800 px-2 py-1 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
        value={to}
        onChange={e => setTo(e.target.value)}
        required
      >
        <option value="">To…</option>
        {entities.map(e => <option key={e}>{e}</option>)}
      </select>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <button className="rounded bg-emerald-600 py-1 text-sm font-medium hover:bg-emerald-500 transition-colors">
        Connect
      </button>
    </form>
  );
}
