// Fixed color assignment per brand so the same brand always gets the same
// line/bar color across turns. Order mirrors data/processed/brand_stats.csv
// (the five brands the dataset actually covers); this is a UI convenience,
// not a data source -- brands not in this list still render, just cycling
// through the same palette by index.
export const KNOWN_BRAND_ORDER = ["Audi", "BMW", "INFINITI", "Lexus", "Mercedes-Benz"];

const PALETTE = [
  "var(--line-1)",
  "var(--line-2)",
  "var(--line-3)",
  "var(--line-4)",
  "var(--line-5)",
];

export function colorForBrand(brand: string): string {
  const idx = KNOWN_BRAND_ORDER.indexOf(brand);
  return PALETTE[(idx >= 0 ? idx : brand.length) % PALETTE.length];
}
