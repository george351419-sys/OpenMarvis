export interface FileLine { name: string; path: string }

export function parseFileLines(body: string): FileLine[] {
  return body.split("\n").map((line) => line.trim()).filter(Boolean)
    .map((line) => {
      const m = /^\[([^\]]+)\]\(<([^>]+)>\)/.exec(line);
      return m ? { name: m[1], path: m[2] } : null;
    })
    .filter((x): x is FileLine => x !== null);
}
