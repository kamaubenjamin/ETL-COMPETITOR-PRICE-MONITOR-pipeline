export function containsPrivilegedKeyPattern(value) {
  const text = String(value);
  if (/sb_secret_[A-Za-z0-9_-]{20,}|postgres(?:ql)?:\/\/|SUPABASE_JWT_SECRET/i.test(text)) return true;
  for (const candidate of text.match(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g) ?? []) {
    try {
      const encoded = candidate.split(".")[1];
      const payload = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8"));
      if (payload?.role === "service_role") return true;
    } catch {
      // Non-JWT bundle text is not credential evidence.
    }
  }
  return false;
}
