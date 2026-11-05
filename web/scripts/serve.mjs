import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import { startupMode } from "../lib/build-mode.mjs";

const command = process.argv[2] === "start" ? "start" : "dev";
const built =
  command === "start"
    ? JSON.parse(
        readFileSync(
          new URL("../.next/required-server-files.json", import.meta.url),
          "utf8",
        ),
      ).config.env?.NEXT_PUBLIC_API_MODE
    : undefined;
const mode = startupMode(command, process.env.API_MODE, built);
const env = { ...process.env, API_MODE: mode, NEXT_TELEMETRY_DISABLED: "1" };
const children = [];
if (mode === "mock") {
  children.push(
    spawn(
      process.execPath,
      [fileURLToPath(new URL("./mock-server.mjs", import.meta.url))],
      { env, stdio: "inherit" },
    ),
  );
}
children.push(
  spawn(
    process.execPath,
    [
      fileURLToPath(
        new URL("../node_modules/next/dist/bin/next", import.meta.url),
      ),
      command,
      "--hostname",
      "127.0.0.1",
      "--port",
      process.env.PORT ?? "3000",
    ],
    { env, stdio: "inherit" },
  ),
);

function stop() {
  for (const child of children) child.kill();
}
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
for (const child of children)
  child.on("exit", (code) => {
    stop();
    process.exitCode = code ?? 0;
  });
