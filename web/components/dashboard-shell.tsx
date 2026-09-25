"use client";

import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useMockBundle } from "@/lib/use-mock-bundle";
import type { MockBundle } from "@/lib/mock-types";

type DashboardShellProps = {
  children: (bundle: MockBundle) => ReactNode;
};

export const DashboardShell = ({ children }: DashboardShellProps) => {
  const { bundle, loading, error } = useMockBundle();

  if (loading) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading mock book…
      </p>
    );
  }

  if (error || !bundle) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Dashboard data unavailable</AlertTitle>
        <AlertDescription>
          {error ?? "Mock bundle did not load."} Start the API with{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">
            ./run_api.sh
          </code>{" "}
          and refresh.
        </AlertDescription>
      </Alert>
    );
  }

  return <>{children(bundle)}</>;
};
