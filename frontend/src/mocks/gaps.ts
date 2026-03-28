export const MOCK_GAPS = {
  citation_gaps: [
    {
      paper: { id: "1", title: "Attention Is All You Need", authors: ["Vaswani et al."], year: 2017, url: "#" },
      cited_by_count: 5,
      cited_by_papers: ["Paper A", "Paper B", "Paper C", "Paper D", "Paper E"],
      why_matters: "Foundational work on transformer architecture cited heavily across your corpus."
    }
  ],
  semantic_gaps: [
    {
      cluster_label: "Mechanistic Interpretability",
      coverage_score: 0.12,
      top_papers: [{ id: "2", title: "Towards Monosemanticity", semantic_score: 0.91 }],
      why_matters: "Your papers frequently reference this topic but you have no direct coverage."
    }
  ]
}
