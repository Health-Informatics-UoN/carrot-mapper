/** Check an ORCID iD using ISO 7064 Mod 11-2 (including its check digit). */
export function isValidOrcid(value: string): boolean {
  const normalised = value.trim().toUpperCase();
  if (!/^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$/.test(normalised)) return false;

  const digits = normalised.replaceAll("-", "");
  let total = 0;
  for (const digit of digits.slice(0, 15)) {
    total = (total + Number(digit)) * 2;
  }
  const remainder = total % 11;
  const result = (12 - remainder) % 11;
  const expected = result === 10 ? "X" : String(result);
  return digits[15] === expected;
}

export function normaliseOrcid(value: string): string {
  return value.trim().toUpperCase();
}
