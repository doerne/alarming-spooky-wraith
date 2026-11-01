/** Kebab-case für Test-IDs, auch aus Werten wie "crates.io" oder "PyPI". */
export function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}
