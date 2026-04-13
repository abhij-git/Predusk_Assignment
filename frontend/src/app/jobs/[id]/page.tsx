"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { finalizeJob, getJob, jobEventsUrl, retryJob, updateReviewed } from "@/lib/api";
import type { JobDetail, ProgressPayload } from "@/lib/types";

export default function JobDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [log, setLog] = useState<ProgressPayload[]>([]);
  const [draft, setDraft] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    try {
      const j = await getJob(id);
      setJob(j);
      const source = j.reviewed_result_json ?? j.result_json;
      setDraft(source ? JSON.stringify(source, null, 2) : "");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to load job");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    const es = new EventSource(jobEventsUrl(id));
    es.onmessage = (ev) => {
      try {
        const p = JSON.parse(ev.data) as ProgressPayload;
        setLog((prev) => [...prev.slice(-40), p]);
      } catch {
        /* ignore */
      }
    };
    es.onerror = () => {
      es.close();
    };
    return () => es.close();
  }, [id]);

  useEffect(() => {
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);

  const finalized = Boolean(job?.finalized_at);
  const canEdit = job?.status === "completed" && !finalized;

  const progressBar = useMemo(() => job?.progress_percent ?? 0, [job?.progress_percent]);

  async function onSave() {
    setErr(null);
    setMsg(null);
    if (!canEdit) return;
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(draft) as Record<string, unknown>;
    } catch {
      setErr("Invalid JSON");
      return;
    }
    setBusy(true);
    try {
      await updateReviewed(id, parsed);
      setMsg("Saved draft");
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onFinalize() {
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      await finalizeJob(id);
      setMsg("Finalized");
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Finalize failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRetry() {
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      await retryJob(id);
      setLog([]);
      setMsg("Job re-queued");
      await load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setBusy(false);
    }
  }

  if (!Number.isFinite(id)) {
    return <p className="text-sm text-red-600">Invalid job id</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/jobs" className="text-sm text-zinc-600 hover:underline dark:text-zinc-400">
          ← Jobs
        </Link>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Job #{id}</h1>
        {job && (
          <span className="rounded-full bg-zinc-200 px-2 py-0.5 text-xs font-medium dark:bg-zinc-800">{job.status}</span>
        )}
      </div>

      {job && (
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <p className="text-sm text-zinc-800 dark:text-zinc-200">
            <span className="font-medium">File:</span> {job.document.original_filename}
          </p>
          <div className="mt-3 h-2 w-full overflow-hidden rounded bg-zinc-100 dark:bg-zinc-800">
            <div className="h-full bg-zinc-900 transition-all dark:bg-zinc-100" style={{ width: `${progressBar}%` }} />
          </div>
          <p className="mt-1 text-xs text-zinc-500">{job.current_stage ?? "—"} · {progressBar}%</p>
          {job.error_message && <p className="mt-2 text-sm text-red-600">{job.error_message}</p>}
        </div>
      )}

      <section className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Live progress (SSE + Redis Pub/Sub)</h2>
        <ul className="mt-2 max-h-48 overflow-auto font-mono text-xs text-zinc-600 dark:text-zinc-400">
          {log.map((l, i) => (
            <li key={i}>
              {l.event} {l.progress_percent != null ? `(${l.progress_percent}%)` : ""} {l.stage ? `— ${l.stage}` : ""}
            </li>
          ))}
          {!log.length && <li className="text-zinc-400">Waiting for events…</li>}
        </ul>
      </section>

      <section className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Review & edit (JSON)</h2>
        <p className="mt-1 text-xs text-zinc-500">
          {finalized ? "This job is finalized; edits are locked." : canEdit ? "Edit fields, save, then finalize." : "Available when status is completed."}
        </p>
        <textarea
          className="mt-3 h-64 w-full rounded border border-zinc-300 bg-zinc-50 p-3 font-mono text-xs text-zinc-900 dark:border-zinc-600 dark:bg-zinc-950 dark:text-zinc-100"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={!canEdit || busy}
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!canEdit || busy}
            onClick={onSave}
            className="rounded-lg bg-zinc-900 px-3 py-1.5 text-sm text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
          >
            Save edits
          </button>
          <button
            type="button"
            disabled={job?.status !== "completed" || finalized || busy}
            onClick={onFinalize}
            className="rounded-lg border border-emerald-600 px-3 py-1.5 text-sm text-emerald-800 disabled:opacity-40 dark:text-emerald-400"
          >
            Finalize
          </button>
          <button
            type="button"
            disabled={busy || job?.status === "processing" || job?.status === "queued" || finalized}
            onClick={onRetry}
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm disabled:opacity-40 dark:border-zinc-600"
          >
            Retry job
          </button>
        </div>
      </section>

      {msg && <p className="text-sm text-emerald-700 dark:text-emerald-400">{msg}</p>}
      {err && <p className="text-sm text-red-600">{err}</p>}
    </div>
  );
}
