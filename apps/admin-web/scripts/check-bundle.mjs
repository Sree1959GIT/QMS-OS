// Nothing secret in the client (R-70): the sources read no environment value beyond Vite's built-in mode flags,
// and the built bundle contains no environment variable names, local paths, private keys or the session cookie name.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
}

const problems = [];
for (const f of files("src")) {
  const text = readFileSync(f, "utf8");
  for (const m of text.matchAll(/import\.meta\.env\.(\w+)/g)) {
    if (!["MODE", "DEV", "PROD"].includes(m[1])) {
      problems.push(`${f}: reads import.meta.env.${m[1]}`);
    }
  }
}
const FORBIDDEN = [/QMS_[A-Z_]+/, /BEGIN [A-Z ]*PRIVATE KEY/, /[A-Za-z]:\\\\Users\\\\/, /qms_session/];
for (const f of files("dist")) {
  const text = readFileSync(f, "utf8");
  for (const re of FORBIDDEN) {
    if (re.test(text)) {
      problems.push(`${f}: contains ${re}`);
    }
  }
}
console.log(`bundle check: ${problems.length} problem(s)`);
for (const p of problems) {
  console.log(`- ${p}`);
}
process.exit(problems.length ? 1 : 0);
