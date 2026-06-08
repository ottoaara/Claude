"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface BoardConnection {
  company_officer: string;
  company_role: string;
  shared_board: string;
  bank_officer: string;
  bank_role: string;
  bank_role_short: string;
}

interface AlumniConnection {
  company_officer: string;
  company_role: string;
  shared_school: string;
  bank_officer: string;
  bank_role: string;
  bank_role_short: string;
}

interface RelationshipData {
  company_name: string;
  bank_name: string;
  board_connections: BoardConnection[];
  alumni_connections: AlumniConnection[];
}

function ConnectionRow({
  left,
  leftSub,
  badge,
  right,
  rightSub,
  badgeColor,
}: {
  left: string;
  leftSub: string;
  badge: string;
  right: string;
  rightSub: string;
  badgeColor: string;
}) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0">
      {/* Company officer */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-[#333333] truncate">{left}</p>
        <p className="text-xs text-[#888888] truncate">{leftSub}</p>
      </div>

      {/* Shared link badge */}
      <div className="flex-shrink-0 flex flex-col items-center gap-1">
        <span className="text-gray-300 text-xs">——</span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeColor} max-w-[160px] text-center leading-tight`}>
          {badge}
        </span>
        <span className="text-gray-300 text-xs">——</span>
      </div>

      {/* Bank officer */}
      <div className="flex-1 min-w-0 text-right">
        <p className="text-sm font-bold text-[#D71E28] truncate">{right}</p>
        <p className="text-xs text-[#888888] truncate">{rightSub}</p>
      </div>
    </div>
  );
}

export default function RelationshipMap({ companyName }: { companyName: string }) {
  const [data, setData] = useState<RelationshipData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.getRelationshipMap(companyName)
      .then((res: any) => setData(res))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [companyName]);

  if (loading) return (
    <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
      <div className="animate-pulse space-y-3">
        <div className="h-6 bg-gray-100 rounded w-48" />
        <div className="h-4 bg-gray-100 rounded w-full" />
        <div className="h-4 bg-gray-100 rounded w-3/4" />
      </div>
    </div>
  );

  const boardConns = data?.board_connections ?? [];
  const alumniConns = data?.alumni_connections ?? [];
  const bankName = data?.bank_name ?? "Wells Fargo";

  if (boardConns.length === 0 && alumniConns.length === 0) {
    return (
      <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
        <h4 className="text-lg font-bold text-[#D71E28] border-b-4 border-[#D71E28] pb-2 inline-block mb-3 uppercase tracking-wide">
          Relationship Map
        </h4>
        <p className="text-sm text-[#888888]">
          No shared board seats or alumni connections found between {companyName} officers and {bankName} officers.
          Run officer research to populate profile data.
        </p>
      </div>
    );
  }

  // Group board connections by shared board name for a cleaner view
  const boardByShared: Record<string, BoardConnection[]> = {};
  for (const c of boardConns) {
    if (!boardByShared[c.shared_board]) boardByShared[c.shared_board] = [];
    boardByShared[c.shared_board].push(c);
  }

  // Group alumni connections by shared school
  const alumniBySchool: Record<string, AlumniConnection[]> = {};
  for (const c of alumniConns) {
    if (!alumniBySchool[c.shared_school]) alumniBySchool[c.shared_school] = [];
    alumniBySchool[c.shared_school].push(c);
  }

  return (
    <div className="space-y-5">
      {/* Board Interlocks with bank */}
      {boardConns.length > 0 && (
        <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
          <div className="flex items-start justify-between mb-1">
            <h4 className="text-lg font-bold text-[#D71E28] border-b-4 border-[#D71E28] pb-2 inline-block uppercase tracking-wide">
              Shared Board Seats
            </h4>
            <span className="text-xs bg-[#D71E28] text-white font-bold px-2 py-1 rounded">
              {boardConns.length} connection{boardConns.length !== 1 ? "s" : ""}
            </span>
          </div>
          <p className="text-xs text-[#666666] mb-5">
            {companyName} officers who sit on the same external board as a {bankName} board member or executive — a direct warm introduction path.
          </p>

          {Object.entries(boardByShared).map(([board, conns]) => (
            <div key={board} className="mb-5 last:mb-0">
              {/* Board name header */}
              <div className="flex items-center gap-2 mb-2">
                <a
                  href={`https://www.google.com/search?q=${encodeURIComponent(board + " board of directors")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-3 py-1 bg-amber-50 border-2 border-amber-400 rounded-full text-xs font-bold text-amber-900 hover:bg-amber-100 transition-colors"
                >
                  {board}
                </a>
              </div>

              <div className="pl-3 border-l-2 border-amber-300">
                {conns.map((c, i) => (
                  <ConnectionRow
                    key={i}
                    left={c.company_officer}
                    leftSub={c.company_role}
                    badge={board}
                    right={c.bank_officer}
                    rightSub={`${bankName} · ${c.bank_role_short}`}
                    badgeColor="bg-amber-50 border-amber-300 text-amber-800"
                  />
                ))}
              </div>
            </div>
          ))}

          <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-[#666666]">
            <strong className="text-[#333333]">{Object.keys(boardByShared).length}</strong> shared external board{Object.keys(boardByShared).length !== 1 ? "s" : ""} identified
          </div>
        </div>
      )}

      {/* Alumni Network */}
      {alumniConns.length > 0 && (
        <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
          <div className="flex items-start justify-between mb-1">
            <h4 className="text-lg font-bold text-[#1a5276] border-b-4 border-[#1a5276] pb-2 inline-block uppercase tracking-wide">
              Alumni Network
            </h4>
            <span className="text-xs bg-[#1a5276] text-white font-bold px-2 py-1 rounded">
              {alumniConns.length} connection{alumniConns.length !== 1 ? "s" : ""}
            </span>
          </div>
          <p className="text-xs text-[#666666] mb-5">
            {companyName} officers who attended the same institution as a {bankName} board member or executive — alumni ties often translate into trusted relationships.
          </p>

          {Object.entries(alumniBySchool).map(([school, conns]) => (
            <div key={school} className="mb-5 last:mb-0">
              {/* School header */}
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 border-2 border-blue-300 rounded-full text-xs font-bold text-blue-900">
                  {school}
                </span>
              </div>

              <div className="pl-3 border-l-2 border-blue-300">
                {conns.map((c, i) => (
                  <ConnectionRow
                    key={i}
                    left={c.company_officer}
                    leftSub={c.company_role}
                    badge={school}
                    right={c.bank_officer}
                    rightSub={`${bankName} · ${c.bank_role_short}`}
                    badgeColor="bg-blue-50 border-blue-300 text-blue-800"
                  />
                ))}
              </div>
            </div>
          ))}

          <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-[#666666]">
            <strong className="text-[#333333]">{Object.keys(alumniBySchool).length}</strong> shared institution{Object.keys(alumniBySchool).length !== 1 ? "s" : ""} identified
          </div>
        </div>
      )}
    </div>
  );
}
