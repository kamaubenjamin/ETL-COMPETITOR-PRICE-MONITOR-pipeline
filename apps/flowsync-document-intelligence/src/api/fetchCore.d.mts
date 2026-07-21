export function resolveFetchImplementation(
  configuredFetch?: typeof fetch,
  browserGlobal?: { fetch?: typeof fetch },
): typeof fetch;
