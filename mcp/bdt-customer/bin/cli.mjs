#!/usr/bin/env node
/**
 * npx launcher for the Python MCP server.
 *
 * Usage:
 *   npx -y @dingjian/customer-mcp
 *   npx -y /absolute/path/to/mcp/bdt-customer
 *
 * IMPORTANT: MCP speaks JSON-RPC over stdout. Never write logs to stdout.
 * All diagnostics go to stderr.
 */
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import https from "node:https";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const PACKAGE_NAME = "@dingjian/customer-mcp";

function readPackageVersion() {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));
    return String(pkg.version || "0.0.0");
  } catch {
    return "0.0.0";
  }
}

const PACKAGE_VERSION = readPackageVersion();
const CACHE_DIR =
  process.env.BDT_CUSTOMER_MCP_CACHE ||
  path.join(
    process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache"),
    "bdt-customer-mcp",
  );
const UV_DIR = path.join(CACHE_DIR, "uv");
// Versioned venv so npm package updates do not reuse a stale environment.
const VENV_DIR = path.join(CACHE_DIR, `venv-${PACKAGE_VERSION}`);

function log(...args) {
  console.error(`[bdt-customer-mcp]`, ...args);
}

function exists(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function which(cmd) {
  const probe = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(probe, [cmd], { encoding: "utf8" });
  if (result.status !== 0) return null;
  const line = (result.stdout || "")
    .split(/\r?\n/)
    .map((s) => s.trim())
    .find(Boolean);
  return line || null;
}

function runSync(command, args, opts = {}) {
  return spawnSync(command, args, {
    encoding: "utf8",
    env: opts.env || process.env,
    cwd: opts.cwd || ROOT,
    shell: opts.shell === true,
  });
}

function runInherit(command, args, opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      // Inherit stdin/stdout/stderr so the Python MCP process owns the MCP pipe.
      stdio: "inherit",
      env: opts.env || process.env,
      cwd: opts.cwd || ROOT,
      shell: opts.shell === true,
    });
    child.on("error", (err) => {
      log(`failed to start ${command}: ${err.message}`);
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

function uvEnv() {
  return {
    ...process.env,
    // Keep the project env outside the npm package directory (npx cache may be ephemeral/read-only).
    UV_PROJECT_ENVIRONMENT: VENV_DIR,
    // Avoid interactive prompts from uv.
    UV_NO_PROGRESS: "1",
  };
}

function resolveUvBinary() {
  const fromPath = which("uv");
  if (fromPath) return fromPath;

  const candidates =
    process.platform === "win32"
      ? [path.join(UV_DIR, "uv.exe"), path.join(UV_DIR, "bin", "uv.exe")]
      : [path.join(UV_DIR, "uv"), path.join(UV_DIR, "bin", "uv")];
  return candidates.find((p) => exists(p)) || null;
}

function downloadText(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (res) => {
        if (
          res.statusCode &&
          res.statusCode >= 300 &&
          res.statusCode < 400 &&
          res.headers.location
        ) {
          downloadText(res.headers.location).then(resolve, reject);
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`GET ${url} -> HTTP ${res.statusCode}`));
          res.resume();
          return;
        }
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      })
      .on("error", reject);
  });
}

async function bootstrapUv() {
  const existing = resolveUvBinary();
  if (existing) return existing;

  ensureDir(UV_DIR);
  log("未检测到 uv，正在安装到本地缓存:", UV_DIR);

  if (process.platform === "win32") {
    // PowerShell installer from Astral.
    const ps = which("powershell") || which("pwsh");
    if (!ps) {
      throw new Error("Windows 上未找到 powershell，无法自动安装 uv");
    }
    const result = runSync(
      ps,
      [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        `irm https://astral.sh/uv/install.ps1 | iex`,
      ],
      {
        env: {
          ...process.env,
          UV_INSTALL_DIR: UV_DIR,
          UV_NO_MODIFY_PATH: "1",
        },
      },
    );
    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || "uv install.ps1 failed");
    }
  } else {
    const script = await downloadText("https://astral.sh/uv/install.sh");
    const child = spawnSync("sh", ["-s"], {
      encoding: "utf8",
      input: script,
      env: {
        ...process.env,
        UV_INSTALL_DIR: UV_DIR,
        UV_NO_MODIFY_PATH: "1",
      },
    });
    if (child.status !== 0) {
      throw new Error(child.stderr || child.stdout || "uv install.sh failed");
    }
  }

  const uv = resolveUvBinary();
  if (!uv) {
    throw new Error(`uv 安装完成但仍未找到可执行文件（期望目录: ${UV_DIR}）`);
  }
  return uv;
}

function syncWithUv(uvPath) {
  ensureDir(CACHE_DIR);
  // First sync may download a managed Python — keep logs on stderr via capture.
  const sync = runSync(uvPath, ["sync", "--directory", ROOT, "--frozen"], {
    env: uvEnv(),
  });
  // --frozen may fail if lockfile absent; retry without it.
  if (sync.status !== 0) {
    const retry = runSync(uvPath, ["sync", "--directory", ROOT], {
      env: uvEnv(),
    });
    if (retry.status !== 0) {
      log(retry.stderr || retry.stdout || "uv sync failed");
      return false;
    }
  }
  return true;
}

function resolveVenvEntry() {
  const candidates = [
    path.join(VENV_DIR, "bin", "bdt-customer-mcp"),
    path.join(VENV_DIR, "Scripts", "bdt-customer-mcp.exe"),
    // Legacy locations from older launcher versions.
    path.join(ROOT, ".venv", "bin", "bdt-customer-mcp"),
    path.join(ROOT, ".venv", "Scripts", "bdt-customer-mcp.exe"),
    path.join(ROOT, ".npx-venv", "bin", "bdt-customer-mcp"),
    path.join(ROOT, ".npx-venv", "Scripts", "bdt-customer-mcp.exe"),
  ];
  return candidates.find((p) => exists(p)) || null;
}

async function ensurePythonEnvWithPip(pythonBin) {
  // Last-resort fallback when uv cannot be installed.
  const marker = path.join(CACHE_DIR, "pip-venv");
  const venvPython =
    process.platform === "win32"
      ? path.join(marker, "Scripts", "python.exe")
      : path.join(marker, "bin", "python");
  const entry =
    process.platform === "win32"
      ? path.join(marker, "Scripts", "bdt-customer-mcp.exe")
      : path.join(marker, "bin", "bdt-customer-mcp");

  if (exists(entry)) return entry;

  ensureDir(CACHE_DIR);
  log("uv 不可用，回退到 python -m venv + pip（需要本机 python3-venv）");
  const venv = runSync(pythonBin, ["-m", "venv", marker]);
  if (venv.status !== 0) {
    log(venv.stderr || "[bdt-customer-mcp] python -m venv failed");
    log(
      "Debian/Ubuntu 请先安装: sudo apt install python3-venv\n" +
        "或安装 uv: https://docs.astral.sh/uv/",
    );
    return null;
  }
  const pipInstall = runSync(venvPython, ["-m", "pip", "install", "--upgrade", "pip"]);
  if (pipInstall.status !== 0) {
    log(pipInstall.stderr || "pip upgrade failed");
  }
  const installPkg = runSync(venvPython, ["-m", "pip", "install", ROOT]);
  if (installPkg.status !== 0) {
    log(installPkg.stderr || "[bdt-customer-mcp] pip install failed");
    return null;
  }
  return exists(entry) ? entry : null;
}

function printVersionAndExit() {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));
    log(`${pkg.name || PACKAGE_NAME} ${pkg.version || "unknown"}`);
    log(`root=${ROOT}`);
    log(`cache=${CACHE_DIR}`);
  } catch (err) {
    log(String(err));
  }
  process.exit(0);
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes("--version") || args.includes("-V")) {
    printVersionAndExit();
  }

  // 1) Prefer an already-prepared entrypoint (cache or legacy).
  const localEntry = resolveVenvEntry();
  if (localEntry) {
    process.exit(await runInherit(localEntry, args));
  }

  // 2) Bootstrap uv (auto-install into user cache if missing), then sync + run.
  try {
    const uv = await bootstrapUv();
    const ok = syncWithUv(uv);
    if (ok) {
      const entry = resolveVenvEntry();
      if (entry) {
        process.exit(await runInherit(entry, args, { env: uvEnv() }));
      }
      process.exit(
        await runInherit(
          uv,
          ["run", "--directory", ROOT, "bdt-customer-mcp", ...args],
          { env: uvEnv() },
        ),
      );
    }
  } catch (err) {
    log(`uv bootstrap failed: ${err instanceof Error ? err.message : String(err)}`);
  }

  // 3) Fallback: system Python 3.10+
  const python =
    which("python3.12") ||
    which("python3.11") ||
    which("python3.10") ||
    which("python3") ||
    which("python");
  if (!python) {
    log(
      "需要 Python 3.10+，或允许自动安装 uv（https://docs.astral.sh/uv/）。\n" +
        "推荐: curl -LsSf https://astral.sh/uv/install.sh | sh",
    );
    process.exit(1);
  }

  const entry = await ensurePythonEnvWithPip(python);
  if (!entry) {
    log("无法准备 Python 运行环境");
    process.exit(1);
  }
  process.exit(await runInherit(entry, args));
}

main().catch((err) => {
  log(err instanceof Error ? err.stack || err.message : String(err));
  process.exit(1);
});
