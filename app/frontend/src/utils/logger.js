/** Frontend logging utility.
 *
 * Log format:  ``<timestamp> <file>:<logtype>: <message>``
 *
 * Usage:
 *   import { getLogger } from "./logger.js";
 *   const logger = getLogger(import.meta.url);
 *   logger.info("GET %s status=%d", path, 200);
 */

const MODULE_NAME = "app-frontend";

function _moduleNameFromUrl(url) {
  try {
    const parsed = new URL(url);
    const pathname = parsed.pathname;
    const last = pathname.split("/").pop();
    return (last || "").replace(/\.m?js$/, "");
  } catch {
    return "unknown";
  }
}

/** Convert Python-style format strings (``%s``, ``%d``) to JS template strings. */
function _interpolate(fmt, args) {
  let i = 0;
  return fmt.replace(/%(s|d)/g, (_, type) => {
    if (i >= args.length) return "";
    const val = args[i];
    if (type === "d") return Number(val).toString();
    i++;
    return val;
  });
}

function _log(level, color, module, rawMsg, ...args) {
  const ts = new Date().toISOString();
  const msg = args.length ? _interpolate(rawMsg, args) : rawMsg;
  const tag = `${MODULE_NAME}:${module}:${level}`;
  const prefix = `${ts} ${tag}: `;

  if (level === "error") {
    console.error(prefix + msg);
  } else if (level === "warn") {
    console.warn(prefix + msg);
  } else if (level === "debug") {
    console.debug(prefix + msg);
  } else {
    console.info(prefix + msg);
  }
}

export function getLogger(url) {
  const module = _moduleNameFromUrl(url);
  return {
    debug: (msg, ...args) => _log("debug", "#94a3b8", module, msg, ...args),
    info: (msg, ...args) => _log("info", "#60a5fa", module, msg, ...args),
    warn: (msg, ...args) => _log("warn", "#fbbf24", module, msg, ...args),
    error: (msg, ...args) => _log("error", "#f87171", module, msg, ...args),
  };
}
