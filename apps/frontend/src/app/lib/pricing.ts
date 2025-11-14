// FULL FILE — drop in as-is
export function displayPriceCents(basePriceCents: number, devFeePct = 0.02, estGasCents = 15) {
  return Math.round(basePriceCents * (1 + devFeePct)) + estGasCents;
}
