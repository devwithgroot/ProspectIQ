export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const fetchApi = async (
  path: string,
  init: RequestInit = {},
  timeoutMs = 15000,
): Promise<Response> => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(`${API_URL}${path}`, {
      ...init,
      signal: init.signal ?? controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        `API timed out talking to ${API_URL}. Is the server running on 127.0.0.1:8000?`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
};
