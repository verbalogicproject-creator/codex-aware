"use client";

import {
  Background,
  Controls,
  Edge,
  MiniMap,
  Node,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from "@xyflow/react";
import {
  Activity,
  ArrowLeft,
  Check,
  ChevronRight,
  CircleDot,
  Copy,
  Focus,
  Link2,
  Network,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  TerminalSquare,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Safety = "safe" | "protected" | "browser_only" | "forbidden" | "unclassified";
type ApiNode = {
  id: string;
  kind: string;
  label: string;
  project?: string;
  uri?: string;
  safety_class?: Safety;
  summary?: string;
  x: number;
  y: number;
  metadata: Record<string, unknown>;
};
type ApiEdge = { id: string; source: string; target: string; kind: string; label?: string };
type Receipt = {
  id: string;
  trace_id: string;
  command: string;
  status: string;
  payload: {
    proposal?: {
      id: string;
      proposal_hash: string;
      payload: Record<string, string>;
      status: string;
    };
    directive?: { id: string; kind: string; target_ids: string[] };
    observed_effect?: Record<string, unknown>;
    test_result?: Record<string, unknown>;
    [key: string]: unknown;
  };
  created_at: number;
};
type RevealDirective = { id: string; kind: string; target_ids: string[] };

const API = process.env.NEXT_PUBLIC_AWARE_API_URL || "http://localhost:8000";
const WORKSPACE = "default";
const incidentIds = ["command:team-todo:delete_task", "command:neon-battleship:fire_at"];

function safetyColor(safety?: Safety) {
  if (safety === "protected") return "#62e6a6";
  if (safety === "unclassified") return "#ffbc5b";
  if (safety === "forbidden") return "#ff6d7a";
  if (safety === "safe") return "#67d8ff";
  return "#8ea0b7";
}

function AppNode({ data, selected }: { data: ApiNode; selected: boolean }) {
  return (
    <div className={`graph-node kind-${data.kind} ${selected ? "selected" : ""}`} style={{ "--node-accent": safetyColor(data.safety_class) } as React.CSSProperties}>
      <span className="node-kind">{data.kind}</span>
      <strong>{data.label}</strong>
      {data.safety_class && <span className={`policy policy-${data.safety_class}`}>{data.safety_class.replace("_", " ")}</span>}
      {data.summary && <small>{data.summary}</small>}
    </div>
  );
}

const nodeTypes = { aware: AppNode };

function Workspace() {
  const [apiNodes, setApiNodes] = useState<ApiNode[]>([]);
  const [apiEdges, setApiEdges] = useState<ApiEdge[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [highlighted, setHighlighted] = useState<string[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [pairCode, setPairCode] = useState<string | null>(null);
  const [pairing, setPairing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [connected, setConnected] = useState(false);
  const [lens, setLens] = useState<"portfolio" | "incident" | "receipt">("portfolio");
  const [activeReceipt, setActiveReceipt] = useState<Receipt | null>(null);
  const [context, setContext] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("Select a node to establish shared context.");
  const ws = useRef<WebSocket | null>(null);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const selectionRequest = useRef<AbortController | null>(null);
  const lastSelectionKey = useRef("");
  const pairCodeButton = useRef<HTMLButtonElement | null>(null);
  const consumingDirectives = useRef(new Set<string>());
  const { fitView } = useReactFlow();

  const fetchGraph = useCallback(async () => {
    const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/graph`);
    if (!response.ok) throw new Error("Graph unavailable");
    const graph = await response.json();
    setApiNodes(graph.nodes);
    setApiEdges(graph.edges);
  }, []);

  const fetchReceipts = useCallback(async (): Promise<Receipt[]> => {
    const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/receipts`);
    if (!response.ok) return [];
    const nextReceipts: Receipt[] = await response.json();
    setReceipts(nextReceipts);
    return nextReceipts;
  }, []);

  const consumeReveal = useCallback(async (receiptId: string, directive: RevealDirective) => {
    if (consumingDirectives.current.has(directive.id)) return;
    consumingDirectives.current.add(directive.id);

    try {
      // A receipt detail swaps in the architecture trace graph. Restore the
      // running application graph before claiming that its nodes were shown.
      await fetchGraph();
      setHighlighted(directive.target_ids);
      setLens("incident");
      setActiveReceipt(null);
      setNotice(`Observed blast radius across ${directive.target_ids.length} semantic entities.`);

      // Let React commit and paint the visual effect before emitting the ACK.
      // Dispatch alone is never treated as successful.
      await new Promise<void>((resolve) => {
        const schedule = window.requestAnimationFrame
          ? window.requestAnimationFrame.bind(window)
          : (callback: FrameRequestCallback) => window.setTimeout(callback, 0);
        schedule(() => schedule(() => resolve()));
      });

      const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/effects`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          receipt_id: receiptId,
          directive_id: directive.id,
          observed: {
            target_count: directive.target_ids.length,
            target_ids: directive.target_ids,
          },
        }),
      });
      if (!response.ok) throw new Error("The visual effect could not be acknowledged.");
      await fetchReceipts();
    } catch (error) {
      consumingDirectives.current.delete(directive.id);
      setNotice(error instanceof Error ? error.message : "The pending reveal will retry when this page resumes.");
    }
  }, [fetchGraph, fetchReceipts]);

  const recoverPendingReveal = useCallback(async () => {
    const nextReceipts = await fetchReceipts();
    const pending = nextReceipts.find(
      (receipt) =>
        receipt.status === "awaiting_consumer" &&
        receipt.payload.directive?.kind === "graph.reveal",
    );
    if (pending?.payload.directive) {
      await consumeReveal(pending.id, pending.payload.directive);
    }
  }, [consumeReveal, fetchReceipts]);

  const connect = useCallback(() => {
    const socketUrl = API.replace(/^http/, "ws") + `/ws/${WORKSPACE}`;
    const socket = new WebSocket(socketUrl);
    ws.current = socket;
    socket.onopen = () => {
      setConnected(true);
      socket.send("ready");
      void recoverPendingReveal();
      if (pingTimer.current) clearInterval(pingTimer.current);
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send("poll");
      }, 650);
    };
    socket.onclose = () => {
      setConnected(false);
      if (pingTimer.current) clearInterval(pingTimer.current);
      window.setTimeout(connect, 1800);
    };
    socket.onmessage = async (message) => {
      const event = JSON.parse(message.data);
      if (event.kind === "directive.issued" && event.payload.kind === "graph.reveal") {
        await consumeReveal(event.payload.receipt_id, event.payload);
      }
      if (event.kind === "repository.refreshed") {
        await fetchGraph();
        setNotice("Policy source, test, and graph now agree.");
      }
      if (
        event.kind === "directive.issued" ||
        event.kind === "proposal.created" ||
        event.kind.startsWith("proposal.") ||
        event.kind === "receipt.finalized"
      ) {
        await fetchReceipts();
      }
    };
  }, [consumeReveal, fetchGraph, fetchReceipts, recoverPendingReveal]);

  useEffect(() => {
    fetchGraph().then(() => window.setTimeout(() => fitView({ padding: 0.16 }), 100));
    fetchReceipts();
    connect();
    return () => {
      if (pingTimer.current) clearInterval(pingTimer.current);
      selectionRequest.current?.abort();
      ws.current?.close();
    };
  }, [connect, fetchGraph, fetchReceipts, fitView]);

  useEffect(() => {
    const recoverWhenVisible = () => {
      if (document.visibilityState === "visible") void recoverPendingReveal();
    };
    document.addEventListener("visibilitychange", recoverWhenVisible);
    window.addEventListener("pageshow", recoverWhenVisible);
    window.addEventListener("focus", recoverWhenVisible);
    return () => {
      document.removeEventListener("visibilitychange", recoverWhenVisible);
      window.removeEventListener("pageshow", recoverWhenVisible);
      window.removeEventListener("focus", recoverWhenVisible);
    };
  }, [recoverPendingReveal]);

  useEffect(() => {
    if (!pairCode) return;
    pairCodeButton.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPairCode(null);
        setCopied(false);
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [pairCode]);

  const nodes: Node[] = useMemo(
    () =>
      apiNodes.map((node) => ({
        id: node.id,
        type: "aware",
        position: { x: node.x, y: node.y },
        data: node,
        selected: selected.includes(node.id),
        className: highlighted.includes(node.id) ? "blast-node" : "",
      })),
    [apiNodes, highlighted, selected],
  );

  const edges: Edge[] = useMemo(
    () =>
      apiEdges.map((edge) => ({
        ...edge,
        label: edge.label || edge.kind.replace("_", " "),
        animated: highlighted.includes(edge.source) && highlighted.includes(edge.target),
        style: { stroke: highlighted.includes(edge.source) && highlighted.includes(edge.target) ? "#67d8ff" : "#314256", strokeWidth: 1.5 },
        labelStyle: { fill: "#76889d", fontSize: 9 },
      })),
    [apiEdges, highlighted],
  );

  const chooseNodes = useCallback(async (ids: string[]) => {
    const uniqueIds = [...new Set(ids)];
    const selectionKey = JSON.stringify(uniqueIds);
    if (selectionKey === lastSelectionKey.current) return;

    lastSelectionKey.current = selectionKey;
    setSelected(uniqueIds);
    selectionRequest.current?.abort();
    const controller = new AbortController();
    selectionRequest.current = controller;

    try {
      const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/selection`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ node_ids: uniqueIds }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("Could not share this selection.");
      const data = await response.json();
      const contextResponse = await fetch(`${API}/api/workspaces/${WORKSPACE}/context`, {
        signal: controller.signal,
      });
      if (!contextResponse.ok) throw new Error("Could not resolve this selection.");
      const nextContext = await contextResponse.json();
      if (selectionRequest.current !== controller) return;
      setContext(nextContext);
      setNotice(`${data.selection.length} stable ${data.selection.length === 1 ? "identity" : "identities"} shared with attached actors.`);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (selectionRequest.current === controller) {
        lastSelectionKey.current = "";
        setNotice(error instanceof Error ? error.message : "Selection failed. Tap the node to retry.");
      }
    }
  }, []);

  const createPair = async () => {
    setPairing(true);
    try {
      const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/pair`, { method: "POST" });
      if (!response.ok) throw new Error("Pairing is temporarily unavailable.");
      const data = await response.json();
      if (!data.code) throw new Error("Pairing code was not returned.");
      setCopied(false);
      setPairCode(data.code);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Pairing failed. Please try again.");
    } finally {
      setPairing(false);
    }
  };

  const closePair = () => {
    setPairCode(null);
    setCopied(false);
  };

  const copyCode = async () => {
    if (!pairCode) return;
    await navigator.clipboard.writeText(pairCode);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const act = async (command: string, arguments_: Record<string, unknown> = {}) => {
    setBusy(true);
    try {
      const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/actions`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ command, arguments: arguments_ }),
      });
      const receipt = await response.json();
      if (!response.ok) throw new Error(receipt.detail || "Action failed");
      await fetchReceipts();
      setActiveReceipt(receipt);
      setNotice(receipt.status === "awaiting_approval" ? "Human authority is required for this durable policy change." : "Semantic directive issued; waiting for observed effect.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const approve = async (receipt: Receipt, decision: "approved" | "rejected") => {
    if (!receipt.payload.proposal) return;
    const proposal = receipt.payload.proposal;
    const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/proposals/${proposal.id}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ proposal_hash: proposal.proposal_hash, decision }),
    });
    if (!response.ok) {
      setNotice("The proposal is stale or no longer matches this approval.");
      return;
    }
    setNotice(decision === "approved" ? "Approved once. Codex may now apply the exact adapter patch." : "Proposal rejected. No source or policy changed.");
    await fetchReceipts();
  };

  const reset = async () => {
    selectionRequest.current?.abort();
    lastSelectionKey.current = "";
    await fetch(`${API}/api/workspaces/${WORKSPACE}/reset`, { method: "POST" });
    setSelected([]);
    setHighlighted([]);
    setActiveReceipt(null);
    setContext(null);
    setLens("portfolio");
    setPairCode(null);
    await Promise.all([fetchGraph(), fetchReceipts()]);
    setNotice("Workspace reset to its original unresolved state.");
    window.setTimeout(() => fitView({ padding: 0.16 }), 80);
  };

  const revealArchitecture = async (receipt: Receipt) => {
    selectionRequest.current?.abort();
    lastSelectionKey.current = "";
    const response = await fetch(`${API}/api/workspaces/${WORKSPACE}/architecture`);
    const graph = await response.json();
    setApiNodes(graph.nodes);
    setApiEdges(graph.edges);
    setSelected([]);
    setHighlighted(["aware:receipt"]);
    setActiveReceipt(receipt);
    setLens("receipt");
    setNotice("This receipt is part of the same graph that explains how it was produced.");
    window.setTimeout(() => fitView({ padding: 0.2 }), 100);
  };

  const returnToWorkspace = async () => {
    await fetchGraph();
    setLens("portfolio");
    setHighlighted([]);
    setActiveReceipt(null);
    window.setTimeout(() => fitView({ padding: 0.16 }), 80);
  };

  const selectedNodes = apiNodes.filter((node) => selected.includes(node.id));
  const pendingReceipt = receipts.find((receipt) => receipt.status === "awaiting_approval");

  return (
    <main>
      <header>
        <div className="brand">
          <div className="brand-mark"><CircleDot size={22} /></div>
          <div><strong>Codex Aware</strong><span>Application continuity</span></div>
        </div>
        <div className="header-actions">
          <span className={`connection ${connected ? "online" : ""}`} role="status">
            <span />{connected ? "Live" : "Reconnecting"}
          </span>
          <button className="secondary" onClick={reset} aria-label="Reset workspace"><RotateCcw size={16} /> Reset</button>
          <button
            aria-expanded={Boolean(pairCode)}
            aria-haspopup="dialog"
            className="primary"
            disabled={pairing}
            onClick={createPair}
          >
            <Link2 size={16} /> {pairing ? "Pairing…" : "Pair Codex"}
          </button>
        </div>
      </header>

      {pairCode && (
        <div className="pair-overlay" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closePair();
        }}>
          <section
            aria-describedby="pair-description"
            aria-labelledby="pair-title"
            aria-modal="true"
            className="panel pair-panel pair-dialog"
            role="dialog"
          >
            <div className="panel-title" id="pair-title"><TerminalSquare size={16} /> Attach Codex</div>
            <p id="pair-description">Use this single-use code from the Codex Aware plugin. It expires in five minutes.</p>
            <button aria-label={`Copy pairing code ${pairCode}`} className="pair-code" onClick={copyCode} ref={pairCodeButton}>
              {pairCode}<span>{copied ? <Check size={15} /> : <Copy size={15} />}</span>
            </button>
            <button className="close-pair" onClick={closePair} aria-label="Close pairing"><X size={16} /></button>
          </section>
        </div>
      )}

      <section className="hero">
        <div>
          <p className="eyebrow">SEMANTIC CONTINUITY FOR RUNNING SOFTWARE</p>
          <h1>Point at your running software.<br /><span>Codex already knows what you mean.</span></h1>
        </div>
        <div className="lens-switch" aria-label="Workspace lens">
          {(["portfolio", "incident", "receipt"] as const).map((item) => (
            <button key={item} className={lens === item ? "active" : ""} onClick={() => setLens(item)}>{item}</button>
          ))}
        </div>
      </section>

      <section className="workspace">
        <div className="canvas-shell">
          <div className="canvas-toolbar">
            {lens === "receipt" ? (
              <button className="text-button" onClick={returnToWorkspace}><ArrowLeft size={15} /> Back to applications</button>
            ) : (
              <>
                <button className="text-button" onClick={() => chooseNodes(incidentIds)}><Focus size={15} /> Select active incident</button>
                <span>Capability safety drift</span>
              </>
            )}
          </div>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(event, node) => {
              event.preventDefault();
              event.stopPropagation();
              void chooseNodes([node.id]);
            }}
            nodesDraggable={false}
            fitView
            minZoom={0.35}
            maxZoom={1.8}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#1f2b38" gap={28} size={1} />
            <Controls showInteractive={false} />
            <MiniMap nodeColor={(node) => safetyColor((node.data as unknown as ApiNode).safety_class)} maskColor="rgba(7,12,18,.72)" />
          </ReactFlow>
          <div className="status-strip" role="status"><Activity size={14} /> {notice}</div>
        </div>

        <aside>
          <div className="panel">
            <div className="panel-title"><Network size={16} /> Shared context</div>
            {selectedNodes.length ? selectedNodes.map((node) => (
              <div className="selection-card" key={node.id}>
                <span>{node.project || "Codex Aware"}</span>
                <strong>{node.label}</strong>
                <small>{node.uri || node.summary}</small>
                {node.safety_class && <em style={{ color: safetyColor(node.safety_class) }}>{node.safety_class.replace("_", " ")}</em>}
              </div>
            )) : <p>Select a node. Its stable identity—not screen coordinates—becomes shared context.</p>}
            {context && <div className="context-proof"><ShieldCheck size={15} /><span>Grounded in application-owned identities</span></div>}
          </div>

          {lens !== "receipt" && (
            <div className="panel">
              <div className="panel-title"><Activity size={16} /> Semantic actions</div>
              <button className="action-row" disabled={busy || !selected.length} onClick={() => act("reveal_blast_radius")}>
                <span><strong>Reveal blast radius</strong><small>Safe visual command</small></span><ChevronRight size={17} />
              </button>
              <button className="action-row" disabled={busy || !selected.includes(incidentIds[0])} onClick={() => act("classify_command", { node_id: incidentIds[0], safety_class: "protected", confirmation_policy: "human_approval" })}>
                <span><strong>Propose safe boundary</strong><small>Human confirmation required</small></span><ChevronRight size={17} />
              </button>
            </div>
          )}

          {pendingReceipt?.payload.proposal && (
            <div className="panel approval-panel">
              <div className="panel-title"><ShieldCheck size={16} /> Approval required</div>
              <p>Classify <code>delete_task</code> as protected and require human approval.</p>
              <dl>
                <div><dt>Target</dt><dd>Team Todo adapter</dd></div>
                <div><dt>Scope</dt><dd>One policy field</dd></div>
                <div><dt>Execution</dt><dd>No task is deleted</dd></div>
              </dl>
              <div className="approval-actions">
                <button className="secondary" onClick={() => approve(pendingReceipt, "rejected")}>Reject</button>
                <button className="approve" onClick={() => approve(pendingReceipt, "approved")}><Check size={15} /> Approve once</button>
              </div>
              <small className="hash">Proposal {pendingReceipt.payload.proposal.proposal_hash.slice(0, 12)}</small>
            </div>
          )}

          <div className="panel receipts-panel">
            <div className="panel-title"><CircleDot size={16} /> Continuity receipts</div>
            {receipts.length === 0 ? <p>No actions yet. Receipts appear only after a declared request.</p> : receipts.slice(0, 5).map((receipt) => (
              <button className="receipt-row" key={receipt.id} onClick={() => revealArchitecture(receipt)}>
                <span className={`receipt-dot status-${receipt.status}`} />
                <span><strong>{receipt.command.replaceAll("_", " ")}</strong><small>{receipt.status.replaceAll("_", " ")}</small></span>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>

          {lens === "receipt" && activeReceipt && (
            <div className="panel receipt-detail">
              <div className="panel-title"><ShieldCheck size={16} /> Causal receipt</div>
              <dl>
                <div><dt>Trace</dt><dd>{activeReceipt.trace_id.slice(0, 12)}</dd></div>
                <div><dt>Status</dt><dd>{activeReceipt.status}</dd></div>
                <div><dt>Grounding</dt><dd>Stable graph identities</dd></div>
                <div><dt>Authority</dt><dd>{activeReceipt.payload.proposal ? "Browser human" : "Declared safe"}</dd></div>
                <div><dt>Effect</dt><dd>{activeReceipt.payload.observed_effect ? "Observed" : "Pending"}</dd></div>
              </dl>
            </div>
          )}
        </aside>
      </section>

      <footer>
        <span>Application-owned identity</span><span>Human authority</span><span>Observed effects</span><span>Durable continuity</span>
      </footer>
    </main>
  );
}

export default function Home() {
  return <ReactFlowProvider><Workspace /></ReactFlowProvider>;
}
