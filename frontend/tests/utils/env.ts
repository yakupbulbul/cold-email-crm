import fs from "fs";
import path from "path";

const repoEnvFile = path.resolve(__dirname, "../../../.env");

export function getRepoEnvValue(key: string): string | undefined {
  if (!fs.existsSync(repoEnvFile)) {
    return undefined;
  }

  for (const line of fs.readFileSync(repoEnvFile, "utf8").split(/\r?\n/)) {
    if (!line || line.startsWith("#")) {
      continue;
    }

    const [envKey, ...rest] = line.split("=");
    if (envKey === key) {
      return rest.join("=").trim();
    }
  }

  return undefined;
}
