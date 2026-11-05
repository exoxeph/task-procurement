/** Keep production's rendered mode and its baked API rewrites in agreement. */
export function startupMode(command, requested, built) {
  if (requested && !["live", "mock"].includes(requested)) {
    throw new Error("API_MODE must be live or mock.");
  }
  if (command === "dev") return requested ?? "mock";
  const mode = built ?? "live";
  if (requested && requested !== mode) {
    throw new Error(
      "API_MODE differs from the production build. Rebuild with the intended API_MODE before starting.",
    );
  }
  return mode;
}
