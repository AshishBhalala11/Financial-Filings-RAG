import type { QueryResponse, UploadResponse } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      signal: AbortSignal.timeout(5_000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function getErrorMessage(
  response: Response,
  fallback: string
): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>;
    };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail)) {
      const messages = body.detail
        .map((item) => item.msg)
        .filter((message): message is string => Boolean(message));
      return messages.length > 0 ? messages.join("; ") : fallback;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

export async function uploadPdf(file: File): Promise<UploadResponse> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body,
    signal: AbortSignal.timeout(300_000),
  });
  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, `Upload failed (${response.status})`)
    );
  }
  return response.json();
}

export async function askQuestion(
  question: string,
  documentId: string | null
): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(120_000),
    body: JSON.stringify({
      question,
      document_id: documentId,
      evaluate: true,
    }),
  });
  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, `Query failed (${response.status})`)
    );
  }
  return response.json();
}
