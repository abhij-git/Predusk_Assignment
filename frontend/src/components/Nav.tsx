"use client";

import Link from "next/link";
import { exportFinalizedUrl } from "@/lib/api";

export function Nav() {
  return (
    <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3 text-sm">
        <Link href="/" className="font-semibold text-zinc-900 dark:text-zinc-100">
          DocFlow
        </Link>
        <nav className="flex gap-4 text-zinc-600 dark:text-zinc-400">
          <Link href="/upload" className="hover:text-zinc-900 dark:hover:text-zinc-100">
            Upload
          </Link>
          <Link href="/jobs" className="hover:text-zinc-900 dark:hover:text-zinc-100">
            Jobs
          </Link>
        </nav>
        <div className="ml-auto flex gap-3">
          <a
            className="rounded-md border border-zinc-300 px-2 py-1 text-xs hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
            href={exportFinalizedUrl("json")}
            target="_blank"
            rel="noreferrer"
          >
            Export JSON
          </a>
          <a
            className="rounded-md border border-zinc-300 px-2 py-1 text-xs hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
            href={exportFinalizedUrl("csv")}
            target="_blank"
            rel="noreferrer"
          >
            Export CSV
          </a>
        </div>
      </div>
    </header>
  );
}
