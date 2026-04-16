/**
 * Parse a value that may be a JSON-encoded string array or already an array.
 * Returns a string[] suitable for FileUpload's existingFiles prop.
 */
export function parseJsonArray(value: unknown): string[] {
  if (Array.isArray(value)) return value;
  if (typeof value === 'string' && value) {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) return parsed;
    } catch {
      /* not valid JSON */
    }
  }
  return [];
}
