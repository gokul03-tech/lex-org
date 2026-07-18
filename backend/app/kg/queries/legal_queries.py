"""Pre-built Cypher queries for common legal graph traversals.

Query library organized by query type:
- Section lookups
- Precedent searches
- Cross-reference traversals
- Case graph building
"""

from __future__ import annotations


# ── Section Queries ──────────────────────────────────────────
SECTION_BY_NUMBER = """
MATCH (s:Section {section_number: $section_number, act: $act})
RETURN s.section_id AS id, s.title AS title, s.text AS text,
       s.act AS act, s.chapter AS chapter, s.year AS year
LIMIT 1
"""

SECTION_BY_TEXT_SEARCH = """
MATCH (s:Section)
WHERE s.text CONTAINS $search_text
   OR s.title CONTAINS $search_text
RETURN s.section_id AS id, s.title AS title, s.text AS text,
       s.act AS act, s.section_number AS section_number
ORDER BY s.section_number
LIMIT $limit
"""

SECTIONS_BY_ACT = """
MATCH (s:Section {act: $act})
RETURN s.section_id AS id, s.section_number AS section_number,
       s.title AS title, s.chapter AS chapter
ORDER BY s.section_number
"""

RELATED_SECTIONS = """
MATCH (s:Section {section_id: $section_id})-[r]-(related:Section)
RETURN related.section_id AS id, related.section_number AS number,
       related.title AS title, related.act AS act,
       type(r) AS relationship_type, r.reason AS reason,
       r.deterministic AS deterministic
LIMIT $limit
"""

CROSS_CODE_REFERENCES = """
MATCH (s:Section {section_id: $section_id})-[r:CROSS_CODE_PROCEDURE|CROSS_CODE_EVIDENCE]->(target:Section)
RETURN target.section_id AS id, target.section_number AS number,
       target.title AS title, target.act AS act,
       type(r) AS relationship, r.reason AS reason
"""

# ── Precedent / Judgment Queries ─────────────────────────────
PRECEDENT_BY_SECTION = """
MATCH (s:Section {section_id: $section_id})<-[r:REFERENCES]-(j:Judgment)
RETURN j.case_name AS case_name, j.citation AS citation,
       j.court AS court, j.year AS year, j.summary AS summary
ORDER BY j.year DESC
LIMIT $limit
"""

JUDGMENT_CONNECTIONS = """
MATCH (j1:Judgment {case_name: $case_name})-[r]-(related)
RETURN type(r) AS relationship_type, labels(related) AS related_labels,
       related.case_name AS related_name
"""

# ── Case Graph Queries ───────────────────────────────────────
CASE_FULL_GRAPH = """
MATCH (c:Case {id: $case_id})-[r]-(connected)
RETURN c.id AS case_id, type(r) AS relationship_type,
       labels(connected) AS connected_labels,
       connected.id AS connected_id,
       properties(connected) AS connected_properties
"""

CASE_SECTION_REFERENCES = """
MATCH (c:Case {id: $case_id})-[:REFERENCES_SECTION]->(s:Section)
OPTIONAL MATCH (s)-[r]-(related:Section)
RETURN s.section_id AS section_id, s.section_number AS section_number,
       s.title AS title, s.act AS act,
       collect(DISTINCT {type: type(r), target: related.section_id, target_act: related.act}) AS related_sections
"""

CASE_EVIDENCE_GRAPH = """
MATCH (c:Case {id: $case_id})-[:PRESENTS_EVIDENCE]->(e:Evidence)
OPTIONAL MATCH (e)-[r]-(related)
RETURN e.id AS evidence_id, e.type AS evidence_type,
       e.reliability_score AS score,
       collect(DISTINCT {type: type(r), target: related.id}) AS connections
"""

# ── Entity Queries ───────────────────────────────────────────
FIND_ENTITY = """
MATCH (n)
WHERE n.id CONTAINS $entity_id
   OR n.name CONTAINS $entity_name
RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties
LIMIT $limit
"""

ENTITY_CONNECTIONS = """
MATCH (n {id: $entity_id})-[r]-(connected)
RETURN type(r) AS relationship_type,
       labels(connected) AS connected_labels,
       connected.id AS connected_id,
       r.reason AS reason
LIMIT $limit
"""

# ── Analytics Queries ────────────────────────────────────────
MOST_REFERENCED_SECTIONS = """
MATCH (c:Case)-[:REFERENCES_SECTION]->(s:Section)
RETURN s.section_id AS section_id, s.section_number AS number,
       s.act AS act, s.title AS title,
       count(c) AS reference_count
ORDER BY reference_count DESC
LIMIT $limit
"""

SECTION_CO_OCCURRENCE = """
MATCH (s1:Section)<-[:REFERENCES_SECTION]-(c:Case)-[:REFERENCES_SECTION]->(s2:Section)
WHERE s1.section_id < s2.section_id
RETURN s1.section_id AS section_a, s1.act AS act_a,
       s2.section_id AS section_b, s2.act AS act_b,
       count(c) AS co_occurrence_count
ORDER BY co_occurrence_count DESC
LIMIT $limit
"""

CONTRADICTION_CLUSTERS = """
MATCH (c:Case)-[:HAS_CONTRADICTION]->(cont:Contradiction)
WHERE cont.severity IN $severity_levels
RETURN c.id AS case_id, cont.id AS contradiction_id,
       cont.severity AS severity, cont.confidence AS confidence
ORDER BY cont.confidence DESC
"""

# ── Temporal Queries ─────────────────────────────────────────
SECTIONS_BY_ERA = """
MATCH (s:Section)
WHERE s.year <= $year_cutoff
RETURN s.section_id AS id, s.section_number AS number,
       s.act AS act, s.year AS year, s.title AS title
ORDER BY s.year DESC, s.section_number
"""

PREDECESSOR_SUCCESSOR = """
MATCH (old:Section)-[r:CROSS_CODE_HISTORICAL|PREDECESSOR|SUCCESSOR]->(new:Section)
RETURN old.section_id AS old_id, old.act AS old_act,
       new.section_id AS new_id, new.act AS new_act,
       type(r) AS transition_type
"""


# ── Query Registry ───────────────────────────────────────────
QUERY_REGISTRY = {
    "section_by_number": SECTION_BY_NUMBER,
    "section_by_text": SECTION_BY_TEXT_SEARCH,
    "sections_by_act": SECTIONS_BY_ACT,
    "related_sections": RELATED_SECTIONS,
    "cross_code_references": CROSS_CODE_REFERENCES,
    "precedent_by_section": PRECEDENT_BY_SECTION,
    "judgment_connections": JUDGMENT_CONNECTIONS,
    "case_full_graph": CASE_FULL_GRAPH,
    "case_section_references": CASE_SECTION_REFERENCES,
    "case_evidence_graph": CASE_EVIDENCE_GRAPH,
    "find_entity": FIND_ENTITY,
    "entity_connections": ENTITY_CONNECTIONS,
    "most_referenced_sections": MOST_REFERENCED_SECTIONS,
    "section_co_occurrence": SECTION_CO_OCCURRENCE,
    "contradiction_clusters": CONTRADICTION_CLUSTERS,
    "sections_by_era": SECTIONS_BY_ERA,
    "predecessor_successor": PREDECESSOR_SUCCESSOR,
}


def get_query(query_name: str) -> str:
    """Get a named Cypher query template.

    Args:
        query_name: Name from the QUERY_REGISTRY.

    Returns:
        Cypher query string.

    Raises:
        KeyError: If query_name is not found.
    """
    if query_name not in QUERY_REGISTRY:
        available = ", ".join(sorted(QUERY_REGISTRY))
        raise KeyError(f"Unknown query '{query_name}'. Available: {available}")
    return QUERY_REGISTRY[query_name]
