export function resolveFetchImplementation(configuredFetch, browserGlobal = globalThis) {
  if (configuredFetch !== undefined) {
    if (typeof configuredFetch !== "function") throw new TypeError("Fetch implementation is unavailable");
    return (...args) => configuredFetch(...args);
  }
  const nativeFetch = browserGlobal?.fetch;
  if (typeof nativeFetch !== "function") throw new TypeError("Fetch implementation is unavailable");
  return nativeFetch.bind(browserGlobal);
}
