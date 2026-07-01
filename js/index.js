// CJS-style entry: set up DOM globals BEFORE mermaid modules load
// (DOMPurify detects browser environment at module initialization time)
const { JSDOM } = require("jsdom");
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, "navigator", { value: dom.window.navigator, writable: true });
// SVG bounding box API used by mermaid for text sizing; not implemented in jsdom
dom.window.SVGElement.prototype.getBBox = () => ({ x: 0, y: 0, width: 100, height: 30 });

(async function main() {
  const { parseMermaidToExcalidraw } = await import("@excalidraw/mermaid-to-excalidraw");

  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const mermaidSource = Buffer.concat(chunks).toString("utf8").trim();
  if (!mermaidSource) {
    process.stderr.write("No Mermaid source provided on stdin\n");
    process.exit(1);
  }

  const { elements, files } = await parseMermaidToExcalidraw(mermaidSource);

  const output = {
    type: "excalidraw",
    version: 2,
    source: "https://excalidraw.com",
    elements,
    appState: {
      gridSize: null,
      viewBackgroundColor: "#ffffff",
    },
    files: files || {},
  };

  process.stdout.write(JSON.stringify(output));
})().catch((err) => {
  process.stderr.write(String(err) + "\n");
  process.exit(1);
});
