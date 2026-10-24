export const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:9000/api";

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });
  } catch {
    throw new Error(
      "Could not reach your local workspace. Check that the local service is running, then try again.",
    );
  }
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail
          .map((entry: { msg?: string }) => entry.msg || "Invalid input")
          .join(". ")
      : data.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : "That action could not be completed. Please try again.",
    );
  }
  return data as T;
}
