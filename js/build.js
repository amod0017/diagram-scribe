import { build } from "esbuild";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { copyFileSync, mkdirSync } from "fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(__dirname, "../src/diagram_scribe/js");

await build({
  entryPoints: [resolve(__dirname, "index.js")],
  bundle: true,
  platform: "node",
  target: "node18",
  format: "cjs",
  outfile: resolve(outDir, "mermaid_to_excalidraw.bundle.js"),
  external: [],
}).catch(() => process.exit(1));

// Copy jsdom's sync XHR worker (loaded dynamically at runtime, can't be bundled)
const workerSrc = resolve(__dirname, "node_modules/jsdom/lib/jsdom/living/xhr/xhr-sync-worker.js");
copyFileSync(workerSrc, resolve(outDir, "xhr-sync-worker.js"));
