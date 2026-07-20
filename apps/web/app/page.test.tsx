// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@xyflow/react", async () => {
  const React = await import("react");
  return {
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    ReactFlowProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
    useReactFlow: () => ({ fitView: vi.fn() }),
    ReactFlow: ({
      nodes,
      nodeTypes,
      onNodeClick,
    }: {
      nodes: Array<{ id: string; data: Record<string, unknown>; selected?: boolean }>;
      nodeTypes: Record<string, React.ComponentType<{ data: Record<string, unknown>; selected: boolean }>>;
      onNodeClick: (event: React.MouseEvent, node: { id: string }) => void;
    }) => {
      const AwareNode = nodeTypes.aware;
      return (
        <div>
          {nodes.map((node) => (
            <button
              key={node.id}
              data-testid={`node-${node.id}`}
              onClick={(event) => onNodeClick(event, node)}
              type="button"
            >
              <AwareNode data={node.data} selected={Boolean(node.selected)} />
            </button>
          ))}
        </div>
      );
    },
  };
});

import Home from "./page";

const graphNode = {
  id: "command:team-todo:delete_task",
  kind: "command",
  label: "delete_task",
  project: "Team Todo",
  safety_class: "unclassified",
  summary: "Deletes a shared task by stable ID",
  x: 20,
  y: 20,
  metadata: {},
};

class WebSocketMock {
  static OPEN = 1;
  readyState = WebSocketMock.OPEN;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: (() => void) | null = null;

  constructor() {
    queueMicrotask(() => this.onopen?.());
  }

  send() {}
  close() {}
}

describe("mobile graph selection", () => {
  beforeEach(() => {
    vi.stubGlobal("WebSocket", WebSocketMock);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const url = String(input);
        if (url.endsWith("/graph")) {
          return new Response(JSON.stringify({ nodes: [graphNode], edges: [] }), { status: 200 });
        }
        if (url.endsWith("/receipts")) {
          return new Response(JSON.stringify([]), { status: 200 });
        }
        if (url.endsWith("/selection")) {
          return new Response(JSON.stringify({ selection: [graphNode], unchanged: false }), { status: 200 });
        }
        if (url.endsWith("/context")) {
          return new Response(JSON.stringify({ selection: [graphNode], related: [] }), { status: 200 });
        }
        return new Response(JSON.stringify({}), { status: 200 });
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("turns one node tap into exactly one selection request", async () => {
    const view = render(<Home />);
    const node = await screen.findByTestId(`node-${graphNode.id}`);

    fireEvent.click(node);

    await waitFor(() => {
      const selectionCalls = vi.mocked(fetch).mock.calls.filter(([input]) =>
        String(input).endsWith("/selection"),
      );
      expect(selectionCalls).toHaveLength(1);
    });
    view.unmount();
  });
});
