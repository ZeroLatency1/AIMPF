'use client'

import { useEffect, useRef } from 'react'

type GraphNode = {
  id: string
  label: string
}

type GraphEdge = {
  id: string
  source: string
  target: string
  weight: number
}

export default function DependencyGraph({
  nodes,
  edges,
}: {
  nodes: GraphNode[]
  edges: GraphEdge[]
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    let active = true
    let cy: any = null

    ;(async () => {
      const mod = await import('cytoscape')
      if (!active || !ref.current) return
      const cytoscape = mod.default ?? mod

      cy = cytoscape({
        container: ref.current,
        elements: [
        ...nodes.map((n) => ({ data: n })),
        ...edges.map((e) => ({
          data: {
            ...e,
            label: e.weight.toFixed(2),
          },
        })),
        ],
        style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            backgroundColor: '#22d3ee',
            color: '#e2e8f0',
            width: 34,
            height: 34,
          } as any,
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            label: 'data(label)',
            lineColor: '#475569',
            targetArrowColor: '#64748b',
            targetArrowShape: 'triangle',
            color: '#94a3b8',
          } as any,
        },
      ],
        layout: {
          name: 'breadthfirst',
          directed: true,
          padding: 30,
        },
      })
    })().catch(() => {})

    return () => {
      active = false
      cy?.destroy()
    }
  }, [nodes, edges])

  return (
    <div
      ref={ref}
      className="h-[520px] w-full rounded-xl border border-slate-800 bg-slate-950"
    />
  )
}
