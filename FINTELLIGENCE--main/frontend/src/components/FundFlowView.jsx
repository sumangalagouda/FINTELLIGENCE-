import { useEffect, useMemo, useRef, useState } from 'react';
import dagre from 'dagre';
import { ArrowRightLeft, Network } from 'lucide-react';

function clipToNode(from, to, node) {
  if (!from || !to || !node) return from || to;

  const halfW = (node.width || 0) / 2;
  const halfH = (node.height || 0) / 2;
  const left = node.x - halfW;
  const right = node.x + halfW;
  const top = node.y - halfH;
  const bottom = node.y + halfH;
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const candidates = [];

  const pushCandidate = (x, y, t) => {
    if (t > 0 && t <= 1 && Number.isFinite(x) && Number.isFinite(y)) {
      candidates.push({ x, y, t });
    }
  };

  if (dx !== 0) {
    const tLeft = (left - from.x) / dx;
    pushCandidate(left, from.y + dy * tLeft, tLeft);

    const tRight = (right - from.x) / dx;
    pushCandidate(right, from.y + dy * tRight, tRight);
  }

  if (dy !== 0) {
    const tTop = (top - from.y) / dy;
    pushCandidate(from.x + dx * tTop, top, tTop);

    const tBottom = (bottom - from.y) / dy;
    pushCandidate(from.x + dx * tBottom, bottom, tBottom);
  }

  if (!candidates.length) {
    return { x: node.x, y: node.y };
  }

  const chosen = candidates.sort((a, b) => a.t - b.t)[0];
  return { x: chosen.x, y: chosen.y };
}

export default function FundFlowView({
  graph,
  transactions,
  eyebrow = 'GRAPH',
  title = 'Relationship map',
  subtitle = 'Explore the movement of funds through the selected case.',
}) {
  const containerRef = useRef(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      setContainerSize({
        width: container.clientWidth || 0,
        height: container.clientHeight || 0,
      });
    });

    observer.observe(container);
    setContainerSize({
      width: container.clientWidth || 0,
      height: container.clientHeight || 0,
    });

    return () => observer.disconnect();
  }, []);

  const fallbackNodes = useMemo(() => {
    const unique = new Map();
    transactions.forEach((txn) => {
      const sender = txn.sender_account || 'SELF';
      const receiver = txn.receiver_account || 'UNKNOWN';
      if (!unique.has(sender)) unique.set(sender, { id: sender, label: sender });
      if (!unique.has(receiver)) unique.set(receiver, { id: receiver, label: receiver });
    });
    return Array.from(unique.values());
  }, [transactions]);

  const fallbackLinks = useMemo(
    () =>
      transactions
        .filter((txn) => txn.sender_account || txn.receiver_account)
        .map((txn, index) => ({
          id: txn.id || `txn-${index}`,
          source: txn.sender_account || 'SELF',
          target: txn.receiver_account || 'UNKNOWN',
          amount: txn.amount || 0,
          type: txn.type,
        })),
    [transactions],
  );

  const normalizedGraph = useMemo(() => {
    const graphNodes = graph?.nodes || [];
    const graphLinks = graph?.links || graph?.edges || [];
    const nodes = graphNodes.length
      ? graphNodes.map((node) => ({
          id: node.id || node.name || node.label,
          label: node.label || node.id || node.name || 'Account',
          total_sent: Number(node.total_sent || 0),
          total_received: Number(node.total_received || 0),
          transaction_count: Number(node.transaction_count || 0),
          risk_score: Number(node.risk_score || 0),
        }))
      : fallbackNodes;

    const links = graphLinks.length
      ? graphLinks.map((link, index) => ({
          id: link.id || `${link.source}-${link.target}-${link.key || index}`,
          source: typeof link.source === 'object' ? link.source.id : link.source,
          target: typeof link.target === 'object' ? link.target.id : link.target,
          amount: Number(link.amount || link.weight || 0),
          type: link.type,
        }))
      : fallbackLinks;

    return { nodes, links };
  }, [fallbackLinks, fallbackNodes, graph]);

  const layout = useMemo(() => {
    if (!normalizedGraph.nodes.length) return { nodes: [], edges: [], width: 0, height: 0 };

    const width = Math.max(containerSize.width || 960, 960);
    const height = Math.max(containerSize.height || 540, 540);
    const dagreGraph = new dagre.graphlib.Graph({ multigraph: true });

    dagreGraph.setGraph({
      rankdir: 'LR',
      nodesep: 56,
      ranksep: 140,
      edgesep: 22,
      marginx: 32,
      marginy: 32,
    });
    dagreGraph.setDefaultEdgeLabel(() => ({}));

    normalizedGraph.nodes.forEach((node) => {
      const nodeWidth = Math.max(170, Math.min(280, 14 * String(node.label || node.id).length + 52));
      dagreGraph.setNode(node.id, { width: nodeWidth, height: 74, ...node });
    });

    normalizedGraph.links.forEach((link, index) => {
      dagreGraph.setEdge(link.source, link.target, { id: link.id || `edge-${index}` });
    });

    dagre.layout(dagreGraph);

    const dagreNodes = dagreGraph.nodes().map((nodeId) => {
      const node = dagreGraph.node(nodeId);
      return {
        id: nodeId,
        x: node.x,
        y: node.y,
        width: node.width,
        height: node.height,
        label: node.label || nodeId,
        total_sent: node.total_sent,
        total_received: node.total_received,
        transaction_count: node.transaction_count,
        risk_score: node.risk_score,
      };
    });

    const dagreEdges = dagreGraph.edges().map((edge) => {
      const edgeData = dagreGraph.edge(edge);
      return {
        id: edgeData.id || `${edge.v}-${edge.w}-${edge.name || ''}`,
        source: edge.v,
        target: edge.w,
        points: edgeData.points || [],
      };
    });

    const extents = dagreNodes.reduce(
      (acc, node) => ({
        minX: Math.min(acc.minX, node.x - node.width / 2),
        maxX: Math.max(acc.maxX, node.x + node.width / 2),
        minY: Math.min(acc.minY, node.y - node.height / 2),
        maxY: Math.max(acc.maxY, node.y + node.height / 2),
      }),
      { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity },
    );

    return {
      nodes: dagreNodes,
      edges: dagreEdges,
      width: Math.max(extents.maxX - extents.minX + 96, width),
      height: Math.max(extents.maxY - extents.minY + 96, height),
    };
  }, [containerSize.height, containerSize.width, normalizedGraph.links, normalizedGraph.nodes]);

  const renderEdgePath = (edge) => {
    const sourceNode = layout.nodes.find((node) => node.id === edge.source);
    const targetNode = layout.nodes.find((node) => node.id === edge.target);
    if (!sourceNode || !targetNode) return '';

    const rawPoints = edge.points || [];
    const sourceAnchor = clipToNode(
      { x: sourceNode.x, y: sourceNode.y },
      { x: targetNode.x, y: targetNode.y },
      sourceNode,
    );
    const targetAnchor = clipToNode(
      { x: targetNode.x, y: targetNode.y },
      { x: sourceNode.x, y: sourceNode.y },
      targetNode,
    );

    const midPoints = rawPoints.slice(1, -1);
    return [
      `M ${sourceAnchor.x} ${sourceAnchor.y}`,
      ...midPoints.map((point) => `L ${point.x} ${point.y}`),
      `L ${targetAnchor.x} ${targetAnchor.y}`,
    ].join(' ');
  };

  return (
    <section className="stack">
      <div className="metric-grid three">
        <div className="metric">
          <span>Accounts</span>
          <strong>{normalizedGraph.nodes.length}</strong>
          <small>Unique nodes</small>
        </div>
        <div className="metric">
          <span>Edges</span>
          <strong>{normalizedGraph.links.length}</strong>
          <small>Directed relationships</small>
        </div>
        <div className="metric">
          <span>Coverage</span>
          <strong>{transactions.length}</strong>
          <small>Transactions analyzed</small>
        </div>
      </div>

      <div className="flow-panel">
        <div className="flow-panel-head">
          <div>
            <p className="eyebrow">FUND FLOW GRAPH</p>
            <h2>{title}</h2>
            <p className="subcopy">{subtitle}</p>
          </div>
          <div className="flow-meta">
            <span>{eyebrow}</span>
            <span>
              <Network size={14} /> Hierarchical layout
            </span>
            <span>
              <ArrowRightLeft size={14} /> Auto-attached edges
            </span>
          </div>
        </div>

        <div className="flow-canvas" ref={containerRef}>
          <div className="flow-scroll">
            <div className="flow-content" style={{ width: layout.width || '100%', minHeight: layout.height || 540 }}>
              {layout.nodes.length > 0 ? (
                <svg className="flow-svg" viewBox={`0 0 ${layout.width} ${layout.height}`} preserveAspectRatio="none">
                  <defs>
                    <marker
                      id="arrowhead"
                      markerWidth="10"
                      markerHeight="10"
                      refX="8"
                      refY="3"
                      orient="auto"
                      markerUnits="strokeWidth"
                    >
                      <path d="M0,0 L0,6 L9,3 z" fill="#1d4ed8" />
                    </marker>
                  </defs>
                  {layout.edges.map((edge, index) => (
                    <path
                      key={`${edge.id}-${index}`}
                      d={renderEdgePath(edge)}
                      fill="none"
                      stroke="rgba(29, 78, 216, 0.34)"
                      strokeWidth="2"
                      markerEnd="url(#arrowhead)"
                    />
                  ))}
                </svg>
              ) : null}

              <div className="flow-nodes" style={{ width: layout.width || '100%', minHeight: layout.height || 540 }}>
                {layout.nodes.map((node) => (
                  <div
                    className="flow-node"
                    key={node.id}
                    style={{
                      left: node.x,
                      top: node.y,
                      width: node.width,
                      height: node.height,
                      transform: 'translate(-50%, -50%)',
                    }}
                    title={node.id}
                  >
                    <strong>{node.label || node.id}</strong>
                    <span>
                      {node.transaction_count || 0} txns · {Math.round(node.risk_score || 0)} risk
                    </span>
                  </div>
                ))}
                {layout.nodes.length === 0 && <span className="empty-line">Upload or select a case to reconstruct fund flow.</span>}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="panel compact-panel">
        <p className="eyebrow">CIRCULAR PATHS</p>
        <strong>{normalizedGraph.links.length ? `${normalizedGraph.links.length} graph relationship(s) found` : 'SELF - UNKNOWN'}</strong>
      </div>
    </section>
  );
}
