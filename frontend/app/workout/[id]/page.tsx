"use client";

import { use, useEffect, useState } from "react";
import type { SessionSummary } from "@/lib/types";
import { fetchSession, startSession } from "@/lib/api";
import { ActiveWorkout } from "@/components/workout/ActiveWorkout";
import { ErrorState, Skeleton } from "@/components/ui/primitives";

export default function SessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const isNew = id === "new";

  const [session, setSession] = useState<SessionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isNew) {
      // "new" is not used currently; sessions are created from /workout
      return;
    }
    fetchSession(Number(id))
      .then(setSession)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load session")
      );
  }, [id, isNew]);

  if (error) return <ErrorState message={error} />;
  if (!session) return <Skeleton className="mt-4 h-64" />;

  return <ActiveWorkout initial={session} />;
}
