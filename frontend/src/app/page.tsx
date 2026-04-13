import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">DocFlow</h1>
        <p className="mt-2 max-w-xl text-zinc-600 dark:text-zinc-400">
          Upload documents for asynchronous processing. Jobs run in Celery workers; progress streams over Redis Pub/Sub
          (SSE). Review extracted fields, finalize, and export JSON or CSV.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/upload"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
        >
          Upload documents
        </Link>
        <Link
          href="/jobs"
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
        >
          View job dashboard
        </Link>
      </div>
    </div>
  );
}
