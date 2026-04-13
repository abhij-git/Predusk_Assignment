"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { listJobs } from "@/lib/api";
import type { JobStatus, JobSummary } from "@/lib/types";

const statuses: (JobStatus | "")[] = ["", "queued", "processing", "completed", "failed"];

const sortOptions = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "-updated_at", label: "Recently updated" },
  { value: "filename", label: "Filename A–Z" },
  { value: "-filename", label: "Filename Z–A" },
];

function badge(status: JobStatus) {
  const map: Record<JobStatus, string> = {
    queued: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100",
    processing: "bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-100",
    completed: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100",
    failed: "bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100",
  };
  return map[status];
}

export default function JobsPage() {
  const [rows, setRows] = useState<JobSummary[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<JobStatus | "">("");
  const [sort, setSort] = useState("-created_at");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const data = await listJobs({
        search: search || undefined,
        status: status || undefined,
        sort,
      });
      setRows(data);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [search, status, sort]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Jobs</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Search, filter by status, sort. Refreshes every 5s.</p>
        </div>
        <Link
          href="/upload"
          className="inline-flex w-fit rounded-lg bg-zinc-900 px-3 py-1.5 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
        >
          New upload
        </Link>
      </div>

      <div className="flex flex-wrap gap-3 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
        <label className="flex flex-col text-xs text-zinc-500">
          Search filename
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onBlur={load}
            className="mt-1 rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-950 dark:text-zinc-100"
            placeholder="e.g. invoice"
          />
        </label>
        <label className="flex flex-col text-xs text-zinc-500">
          Status
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as JobStatus | "")}
            className="mt-1 rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-950 dark:text-zinc-100"
          >
            {statuses.map((s) => (
              <option key={s || "all"} value={s}>
                {s || "All"}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-xs text-zinc-500">
          Sort
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="mt-1 rounded border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-600 dark:bg-zinc-950 dark:text-zinc-100"
          >
            {sortOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={load}
          className="self-end rounded border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-600"
        >
          Refresh
        </button>
      </div>

      {err && <p className="text-sm text-red-600">{err}</p>}
      {loading && !rows.length ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : (
        <ul className="divide-y divide-zinc-200 overflow-hidden rounded-xl border border-zinc-200 bg-white dark:divide-zinc-800 dark:border-zinc-800 dark:bg-zinc-900">
          {rows.map((j) => (
            <li key={j.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <Link href={`/jobs/${j.id}`} className="font-medium text-zinc-900 hover:underline dark:text-zinc-100">
                #{j.id}
              </Link>
              <span className="text-sm text-zinc-600 dark:text-zinc-400">{j.document.original_filename}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge(j.status)}`}>{j.status}</span>
              <span className="text-xs text-zinc-500">{j.progress_percent}%</span>
              {j.finalized_at && <span className="text-xs text-emerald-700 dark:text-emerald-400">Finalized</span>}
            </li>
          ))}
          {!rows.length && <li className="px-4 py-8 text-center text-sm text-zinc-500">No jobs match.</li>}
        </ul>
      )}
    </div>
  );
}
