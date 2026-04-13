"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { getApiBase, uploadDocuments } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErr(null);
    const input = (e.currentTarget.elements.namedItem("files") as HTMLInputElement) || null;
    const files = input?.files;
    if (!files?.length) {
      setErr("Choose one or more files.");
      return;
    }
    setBusy(true);
    try {
      const res = await uploadDocuments(files);
      const first = res.jobs[0]?.job_id;
      if (first) router.push(`/jobs/${first}`);
      else router.push("/jobs");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      if (msg === "Failed to fetch" || msg.includes("Load failed")) {
        const target = getApiBase() || "http://127.0.0.1:8000 (via Next.js proxy)";
        setErr(
          `Cannot reach the API (${target}). Start Postgres + Redis, then run: cd backend && PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000`,
        );
      } else {
        setErr(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Upload</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Each file creates a document row and a queued processing job handled by a Celery worker.
        </p>
      </div>
      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <input
          name="files"
          type="file"
          multiple
          className="block w-full text-sm text-zinc-700 file:mr-4 file:rounded-md file:border-0 file:bg-zinc-100 file:px-3 file:py-2 file:text-sm dark:text-zinc-300 dark:file:bg-zinc-800"
        />
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {busy ? "Uploading…" : "Upload & process"}
        </button>
      </form>
    </div>
  );
}
