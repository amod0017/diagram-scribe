// CJS-style entry: set up DOM globals BEFORE mermaid modules load
// (DOMPurify detects browser environment at module initialization time)
const { JSDOM } = require("jsdom");
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, "navigator", { value: dom.window.navigator, writable: true });

// Helvetica AFM character advance widths (units per 1000em).
// Source: Adobe Font Metrics for Helvetica (standard PostScript font).
// Used to measure SVG text so node containers are sized to fit their labels.
const HELVETICA_WIDTHS = {
  ' ':278,'!':278,'"':355,'#':556,'$':556,'%':889,'&':667,"'":222,
  '(':333,')':333,'*':389,'+':584,',':278,'-':333,'.':278,'/':278,
  '0':556,'1':556,'2':556,'3':556,'4':556,'5':556,'6':556,'7':556,'8':556,'9':556,
  ':':278,';':278,'<':584,'=':584,'>':584,'?':556,'@':1015,
  'A':667,'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,'H':722,'I':278,
  'J':500,'K':667,'L':611,'M':833,'N':722,'O':778,'P':667,'Q':778,'R':722,
  'S':667,'T':611,'U':722,'V':667,'W':944,'X':667,'Y':667,'Z':611,
  '[':278,'\\':278,']':278,'^':469,'_':556,'`':222,
  'a':556,'b':556,'c':500,'d':556,'e':556,'f':278,'g':556,'h':556,'i':222,
  'j':222,'k':500,'l':222,'m':833,'n':556,'o':556,'p':556,'q':556,'r':333,
  's':500,'t':278,'u':556,'v':500,'w':722,'x':500,'y':500,'z':500,
  '{':334,'|':260,'}':334,'~':584,
};

// Display font size used by @excalidraw/mermaid-to-excalidraw for skeleton label output.
const DISPLAY_FONT_SIZE = 20;

function measureNodeWidth(text) {
  let w = 0;
  for (const ch of text) w += (HELVETICA_WIDTHS[ch] ?? 556) * DISPLAY_FONT_SIZE / 1000;
  return Math.max(w + 40, 80); // 40px horizontal padding, 80px minimum
}

// getBBox polyfill using Helvetica AFM metrics + a queue-based mapping strategy.
//
// How @excalidraw/mermaid-to-excalidraw uses getBBox in jsdom:
//  1. It creates a <foreignObject> with the label text and calls getBBox — the result
//     sets the skeleton element's width/height.
//  2. It later calls getBBox on the <g data-node="true"> wrapper to get the bounding
//     box used by the layout engine. At that point the foreignObject child is an empty
//     placeholder (textContent is empty, querySelectorAll finds nothing).
//
// The layout engine (dagre) runs with hardcoded node sizes and is NOT influenced by
// our getBBox results — only the skeleton element dimensions are. We return correct
// sizes from step 1 and drain the queue in step 2 so skeleton dimensions are accurate.
// Overlaps caused by the layout engine are fixed in fixOverlaps() post-processing.
const _labelSizeQueue = [];

dom.window.SVGElement.prototype.getBBox = function () {
  const text = (this.textContent || '').trim();

  if (text && this.tagName === 'foreignObject') {
    // Step 1: text-bearing foreignObject — measure and enqueue.
    const w = measureNodeWidth(text);
    const h = DISPLAY_FONT_SIZE * 2;
    _labelSizeQueue.push({ w, h });
    return { x: 0, y: 0, width: w, height: h };
  }

  if (this.getAttribute && this.getAttribute('data-node') === 'true' && _labelSizeQueue.length > 0) {
    // Step 2: node bounding-box call — dequeue the matching label size.
    const { w, h } = _labelSizeQueue.shift();
    return { x: 0, y: 0, width: w, height: h };
  }

  return { x: 0, y: 0, width: 10, height: 10 };
};

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

// Fix overlapping nodes that share approximately the same y-level.
// Dagre runs with hardcoded sizes so wide labels can cause siblings to overlap.
// This spreads overlapping same-level nodes apart and rebuilds arrow paths.
function fixOverlaps(skeletonElements) {
  const NODE_GAP = 30; // minimum horizontal gap between nodes on the same level
  const LEVEL_TOLERANCE = 5; // px — nodes within this y-distance are considered same-level

  const nodes = skeletonElements.filter(e => e.type !== 'arrow');
  const arrows = skeletonElements.filter(e => e.type === 'arrow');

  // Group nodes into y-levels
  const levels = [];
  for (const node of nodes) {
    const existing = levels.find(lv => Math.abs(lv.y - node.y) <= LEVEL_TOLERANCE);
    if (existing) {
      existing.nodes.push(node);
    } else {
      levels.push({ y: node.y, nodes: [node] });
    }
  }

  // For each level with multiple nodes, spread if they overlap
  for (const level of levels) {
    if (level.nodes.length < 2) continue;
    level.nodes.sort((a, b) => a.x - b.x);

    let hasOverlap = false;
    for (let i = 1; i < level.nodes.length; i++) {
      const prev = level.nodes[i - 1];
      const curr = level.nodes[i];
      if (prev.x + prev.width + NODE_GAP > curr.x) { hasOverlap = true; break; }
    }
    if (!hasOverlap) continue;

    // Compute total span and re-center around original centroid
    const totalWidth = level.nodes.reduce((s, n) => s + n.width, 0);
    const span = totalWidth + NODE_GAP * (level.nodes.length - 1);
    const centroid = level.nodes.reduce((s, n) => s + n.x + n.width / 2, 0) / level.nodes.length;
    let x = centroid - span / 2;
    for (const node of level.nodes) {
      node.x = x;
      x += node.width + NODE_GAP;
    }
  }

  // Rebuild arrow paths as straight lines between node centers using new positions.
  // (startBinding/endBinding keep interactive drag correct; points drive static rendering.)
  const nodeById = new Map(nodes.map(n => [n.id, n]));
  for (const arrow of arrows) {
    const src = arrow.start ? nodeById.get(arrow.start.id) : null;
    const dst = arrow.end   ? nodeById.get(arrow.end.id)   : null;
    if (!src || !dst) continue;

    const ARROW_GAP = 8;
    const sx = src.x + src.width / 2;
    const sy = src.y + src.height + ARROW_GAP;
    const ex = dst.x + dst.width / 2;
    const ey = dst.y - ARROW_GAP;

    arrow.x = sx;
    arrow.y = sy;
    arrow.points = [[0, 0], [ex - sx, ey - sy]];
  }

  return skeletonElements;
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
        roundness: { type: 2 },
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
  const fixed = fixOverlaps(skeletonElements);
  const elements = convertElements(fixed);

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
