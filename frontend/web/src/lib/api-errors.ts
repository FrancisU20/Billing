export function getApiErrorMessage(error: unknown, fallback = "No se pudo completar la operación") {
  const responseData = (error as { response?: { data?: unknown } })?.response?.data;

  if (typeof responseData === "string") return responseData;

  if (responseData && typeof responseData === "object") {
    const data = responseData as { detail?: unknown; message?: unknown };
    if (typeof data.message === "string") return data.message;
    if (typeof data.detail === "string") return data.detail;
    if (data.detail && typeof data.detail === "object") {
      const detail = data.detail as { message?: unknown };
      if (typeof detail.message === "string") return detail.message;
    }
  }

  const message = (error as { message?: unknown })?.message;
  return typeof message === "string" && message ? message : fallback;
}
