from google.adk.agents import Agent
from app.agents.tools.gap_tools import (
    get_workspace_papers,
    get_citation_gap_papers,
    get_candidate_embeddings,
    run_hdbscan_clustering,
    compute_cluster_coverage,
    label_all_clusters,
    store_blind_spots,
    detect_semantic_gaps,
)

gap_detection_agent = Agent(
    name="gap_detection_agent",
    model="gemini-2.5-flash",
    instruction="""You are a research gap detection specialist for LitLens.
Given a workspace_id, run the full blind spot detection pipeline in order:
1. get_workspace_papers — retrieve what the researcher has read
2. get_citation_gap_papers — Layer 1: papers cited but not in workspace
3. get_candidate_embeddings — embeddings for all citation gap papers
4. run_hdbscan_clustering — cluster the candidate embedding space
5. compute_cluster_coverage — measure how well workspace papers cover each cluster
6. For clusters with coverage < 0.65: call label_all_clusters
7. store_blind_spots — persist all semantic gaps
Finish with: "Found N semantic gaps." """,
    tools=[
        get_workspace_papers,
        get_citation_gap_papers,
        get_candidate_embeddings,
        run_hdbscan_clustering,
        compute_cluster_coverage,
        label_all_clusters,
        store_blind_spots,
        detect_semantic_gaps,
    ]
)
