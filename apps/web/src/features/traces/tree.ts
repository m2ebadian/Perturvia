import type { Span } from "@/features/traces/types";

export interface SpanNode {
  span: Span;
  children: SpanNode[];
}

/** Turn a flat list of spans into a tree using parent_span_id. */
export function buildSpanTree(spans: Span[]): SpanNode[] {
  const nodes = new Map<string, SpanNode>();
  for (const span of spans) {
    nodes.set(span.id, { span, children: [] });
  }

  const roots: SpanNode[] = [];
  for (const span of spans) {
    const node = nodes.get(span.id)!;
    const parent = span.parent_span_id ? nodes.get(span.parent_span_id) : undefined;

    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

/** Flatten the tree into rows in display order, each with its depth. */
export function flattenTree(roots: SpanNode[]): { span: Span; depth: number }[] {
  const rows: { span: Span; depth: number }[] = [];

  function visit(node: SpanNode, depth: number): void {
    rows.push({ span: node.span, depth });
    for (const child of node.children) {
      visit(child, depth + 1);
    }
  }

  for (const root of roots) {
    visit(root, 0);
  }

  return rows;
}
