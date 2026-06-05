"use client";

import { useState } from "react";

export default function AddEntityForm({ api, onDone }: { api: string; onDone: () => void }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("concept");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const res = await fetch(`${api}/entity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, type, attributes: {} }),
    });
    if (!res.ok) {
      const data = await res.json();
      setError(data.detail ?? "Error");
      return;
    }
    setName("");
    onDone();
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2">
      <p className="text-xs text-gray-400 uppercase tracking-wide">Add Entity</p>
      <input
        className="rounded bg-gray-800 px-2 py-1 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
        placeholder="Name"
        value={name}
        onChange={e => setName(e.target.value)}
        required
      />
      <select
        className="rounded bg-gray-800 px-2 py-1 text-sm outline-none focus:ring-1 focus:ring-indigo-500"
        value={type}
        onChange={e => setType(e.target.value)}
      >
        {["concept", "person", "project", "service", "component"].map(t => (
          <option key={t}>{t}</option>
        ))}
      </select>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <button className="rounded bg-indigo-600 py-1 text-sm font-medium hover:bg-indigo-500 transition-colors">
        Add
      </button>
    </form>
  );
}
