export const MOCK_GRAPH = {
  nodes: [
    { id: "1", title: "Attention Is All You Need", year: 2017,
      cluster_id: 0, cluster_color: "#4ECDC4", citation_count: 142, is_blind_spot: false },
    { id: "2", title: "BERT", year: 2018,
      cluster_id: 0, cluster_color: "#4ECDC4", citation_count: 89, is_blind_spot: false },
  ],
  edges: [{ source: "1", target: "2", edge_type: "cites", confidence: 1.0 }],
  clusters: [{ id: 0, label: null, color: "#4ECDC4", size: 2 }]
}
