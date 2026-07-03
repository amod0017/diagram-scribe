// CJS-style entry: set up DOM globals BEFORE mermaid modules load
// (DOMPurify detects browser environment at module initialization time)
const { JSDOM } = require("jsdom");
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, "navigator", { value: dom.window.navigator, writable: true });
// SVG bounding box API used by mermaid for text sizing; not implemented in jsdom
dom.window.SVGElement.prototype.getBBox = () => ({ x: 0, y: 0, width: 100, height: 30 });

const BASE_PROPS = {
  angle: 0,
  strokeColor: "#1e1e1e",
  backgroundColor: "transparent",
  fillStyle: "solid",
  strokeStyle: "solid",
  roughness: 1,
  opacity: 100,
  frameId: null,
  version: 1,
  versionNonce: 0,
  isDeleted: false,
  boundElements: null,
  updated: Date.now(),
  link: null,
  locked: false,
};

function seed() {
  return Math.floor(Math.random() * 99999) + 1;
}

// parseMermaidToExcalidraw returns "skeleton" elements with label/start/end properties
// that are not part of the Excalidraw element schema. This converts them to the proper
// format: labels become bound text elements, start/end become startBinding/endBinding.
function convertElements(skeletonElements) {
  const result = [];

  for (const el of skeletonElements) {
    const { label, start, end, ...rest } = el;
    const hasLabel = label && label.text;
    const textId = `${el.id}_label`;

    if (el.type === "arrow") {
      const arrow = {
        ...BASE_PROPS,
        seed: seed(),
        roundness: el.roundness || { type: 2 },
        lastCommittedPoint: null,
        startArrowhead: null,
        endArrowhead: "arrow",
        ...rest,
        boundElements: hasLabel ? [{ type: "text", id: textId }] : null,
      };
      if (start) arrow.startBinding = { elementId: start.id, focus: 0, gap: 8 };
      if (end) arrow.endBinding = { elementId: end.id, focus: 0, gap: 8 };
      result.push(arrow);
    } else {
      result.push({
        ...BASE_PROPS,
        seed: seed(),
        roundness: el.type === "rectangle" ? { type: 3 } : null,
        ...rest,
        boundElements: hasLabel ? [{ type: "text", id: textId }] : null,
      });
    }

    if (hasLabel) {
      const fontSize = label.fontSize || 20;
      result.push({
        ...BASE_PROPS,
        seed: seed(),
        id: textId,
        type: "text",
        x: el.x,
        y: el.y + ((el.height || 0) - fontSize) / 2,
        width: el.width || 100,
        height: fontSize + 4,
        text: label.text,
        fontSize,
        fontFamily: 1,
        textAlign: "center",
        verticalAlign: "middle",
        containerId: el.id,
        baseline: fontSize - 4,
        groupIds: label.groupIds || [],
      });
    }
  }

  return result;
}

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

  const { elements: skeletonElements, files } = await parseMermaidToExcalidraw(mermaidSource);
  const elements = convertElements(skeletonElements);

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
