#!/usr/bin/env node
/**
 * npx launcher for the Python MCP server.
 *
 * Usage:
 *   npx -y @ouhaibing/customer-mcp
 *   npx -y /absolute/path/to/mcp/bdt-customer
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");

function exists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.X_OK);
    return true;
  } catch {
    try {
      fs.accessSync(filePath, fs.constants.F_OK);
      return true;
    } catch {
      return false;
    }
  }
}

function which(cmd) {
  const probe = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(probe, [cmd], { encoding: "utf8" });
  if (result.status !== 0) return null;
  const line = (result.stdout || "").split(/\r?\n/).map((s) => s.trim()).find(Boolean);
  return line || null;
}

function run(command, args, opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      stdio: "inherit",
      env: process.env,
      cwd: opts.cwd || ROOT,
      shell: opts.shell === true,
    });
    child.on("error", (err) => {
      console.error(`[bdt-customer-mcp] failed to start ${command}: ${err.message}`);
      resolve(1);
    });
    child.on("exit", (code, signal) => {
      if (signal) {
        resolve(1);
        return;
      }
      resolve(code ?? 1);
    });
  });
}

function ensureUvProject() {
  // uv can create/sync a project env from pyproject.toml
  const uv = which("uv");
  if (!uv) return null;
  return uv;
}

async function ensurePythonEnvWithUv(uvPath) {
  const sync = spawnSync(
    uvPath,
    ["sync", "--directory", ROOT],
    { encoding: "utf8", env: process.env },
  );
  if (sync.status !== 0) {
    console.error(sync.stderr || sync.stdout || "[bdt-customer-mcp] uv sync failed");
    return false;
  }
  return true;
}

async function ensurePythonEnvWithPip(pythonBin) {
  const marker = path.join(ROOT, ".npx-venv");
  const venvPython =
    process.platform === "win32"
      ? path.join(marker, "Scripts", "python.exe")
      : path.join(marker, "bin", "python");
  const entry =
    process.platform === "win32"
      ? path.join(marker, "Scripts", "bdt-customer-mcp.exe")
      : path.join(marker, "bin", "bdt-customer-mcp");

  if (!exists(entry)) {
    const venv = spawnSync(pythonBin, ["-m", "venv", marker], {
      encoding: "utf8",
      env: process.env,
    });
    if (venv.status !== 0) {
      console.error(venv.stderr || "[bdt-customer-mcp] python -m venv failed");
      return null;
    }
    const pipInstall = spawnSync(
      venvPython,
      ["-m", "pip", "install", "-e", ROOT],
      { encoding: "utf8", env: process.env },
    );
    if (pipInstall.status !== 0) {
      console.error(pipInstall.stderr || "[bdt-customer-mcp] pip install failed");
      return null;
    }
  }
  return exists(entry) ? entry : null;
}

function resolveLocalVenvEntry() {
  const candidates = [
    path.join(ROOT, ".venv", "bin", "bdt-customer-mcp"),
    path.join(ROOT, ".venv", "Scripts", "bdt-customer-mcp.exe"),
    path.join(ROOT, ".npx-venv", "bin", "bdt-customer-mcp"),
    path.join(ROOT, ".npx-venv", "Scripts", "bdt-customer-mcp.exe"),
  ];
  return candidates.find((p) => exists(p)) || null;
}

async function main() {
  // 1) Prefer existing project/.npx venv entrypoint
  const localEntry = resolveLocalVenvEntry();
  if (localEntry) {
    process.exit(await run(localEntry, process.argv.slice(2)));
  }

  // 2) uv run (best for fresh npx installs)
  const uv = ensureUvProject();
  if (uv) {
    const ok = await ensurePythonEnvWithUv(uv);
    if (ok) {
      process.exit(
        await run(uv, ["run", "--directory", ROOT, "bdt-customer-mcp", ...process.argv.slice(2)]),
      );
    }
  }

  // 3) Fallback: system Python 3.10+
  const python =
    which("python3.12") ||
    which("python3.11") ||
    which("python3.10") ||
    which("python3") ||
    which("python");
  if (!python) {
    console.error(
      "[bdt-customer-mcp] 需要 Python 3.10+ 或安装 uv (https://docs.astral.sh/uv/).\n" +
        "推荐: curl -LsSf https://astral.sh/uv/install.sh | sh",
    );
    process.exit(1);
  }

  const entry = await ensurePythonEnvWithPip(python);
  if (!entry) {
    console.error("[bdt-customer-mcp] 无法准备 Python 运行环境");
    process.exit(1);
  }
  process.exit(await run(entry, process.argv.slice(2)));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
