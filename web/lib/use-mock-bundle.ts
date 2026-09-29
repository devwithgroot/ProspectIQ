"use client";

import { useEffect, useState } from "react";

import { fetchMockBundle } from "@/lib/mock-bundle";
import type { MockBundle } from "@/lib/mock-types";

type MockBundleState = {
  bundle: MockBundle | null;
  loading: boolean;
  error: string | null;
};

export const useMockBundle = (): MockBundleState => {
  const [bundle, setBundle] = useState<MockBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = await fetchMockBundle();
        if (!active) {
          return;
        }
        setBundle(payload);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(
          err instanceof Error
            ? err.message
            : "Could not load mock dashboard data.",
        );
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      active = false;
    };
  }, []);

  return { bundle, loading, error };
};
