/** Client-side mirror of backend/necromancer/github/urls.py, for instant feedback. */
const PATTERNS = [
  /^(?:https?:\/\/)?(?:www\.)?github\.com\/([A-Za-z0-9][A-Za-z0-9-]{0,38})\/([A-Za-z0-9._-]{1,100}?)(?:\.git)?(?:\/(?:tree|blob)\/\S*)?\/?(?:[?#].*)?$/,
  /^git@github\.com:([A-Za-z0-9][A-Za-z0-9-]{0,38})\/([A-Za-z0-9._-]{1,100}?)(?:\.git)?$/,
  /^([A-Za-z0-9][A-Za-z0-9-]{0,38})\/([A-Za-z0-9._-]{1,100}?)$/,
];

export function parseRepo(raw: string): string | null {
  const text = raw.trim();
  for (const pattern of PATTERNS) {
    const m = pattern.exec(text);
    if (m && m[1] && m[2] && m[2] !== "." && m[2] !== "..") return `${m[1]}/${m[2]}`;
  }
  return null;
}
