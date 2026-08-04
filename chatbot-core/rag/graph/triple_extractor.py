"""Deterministic triple extraction for plugin graph chunks."""

import re

from rag.graph.entity_normalizer import resolve_plugin_name
from rag.graph.models import GraphEntity, GraphEvidence, Triple
from rag.graph.schema import GraphEntityType, GraphRelationType


MAX_TARGET_TOKENS = 8
MAX_TARGET_START_OFFSET = 3
TARGET_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+._-]*")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
SKIPPED_TARGET_PLUGIN_IDS = {"jenkins"}

RELATION_PATTERNS = (
    (
        GraphRelationType.OPTIONAL_DEPENDS_ON.value,
        0.75,
        re.compile(
            r"\b(?:optionally depends on|optional dependencies include|"
            r"optional dependency(?: is|:)?|optionally requires)\b",
            re.IGNORECASE,
        ),
    ),
    (
        GraphRelationType.DEPENDS_ON.value,
        0.9,
        re.compile(r"(?<!optionally )\bdepends on\b", re.IGNORECASE),
    ),
    (
        GraphRelationType.DEPENDS_ON.value,
        0.85,
        re.compile(r"(?<!optionally )\brequires?\b", re.IGNORECASE),
    ),
    (
        GraphRelationType.CONFLICTS_WITH.value,
        0.8,
        re.compile(r"\b(?:conflicts? with|incompatible with)\b", re.IGNORECASE),
    ),
)


def make_plugin_entity(plugin_id: str) -> GraphEntity:
    """
    Build a plugin graph entity from a canonical plugin ID.

    Args:
        plugin_id (str): Canonical plugin ID.

    Returns:
        GraphEntity: Plugin graph entity.
    """
    return GraphEntity(
        name=plugin_id,
        entity_type=GraphEntityType.PLUGIN.value,
        entity_id=plugin_id,
    )


def build_chunk_evidence(chunk: dict, evidence_text: str) -> GraphEvidence:
    """
    Build source-backed graph evidence from a chunk.

    Args:
        chunk (dict): Chunk payload from chunks_plugin_docs.json.
        evidence_text (str): Sentence or text span supporting the relation.

    Returns:
        GraphEvidence: Source-grounded evidence payload.
    """
    metadata = chunk.get("metadata", {})
    return GraphEvidence(
        source_chunk_id=chunk.get("id", ""),
        source_title=metadata.get("title", ""),
        source_data_source=metadata.get("data_source", ""),
        evidence=evidence_text.strip(),
    )


def sentence_split(text: str) -> list[str]:
    """
    Split chunk text into simple sentence spans.

    Args:
        text (str): Chunk text to split.

    Returns:
        list[str]: Non-empty sentences.
    """
    return [
        sentence.strip()
        for sentence in SENTENCE_SPLIT_PATTERN.split(text)
        if sentence.strip()
    ]


def build_candidate_variants(candidate: str) -> list[str]:
    """
    Build candidate name variants for alias lookup.

    Args:
        candidate (str): Raw plugin phrase from a sentence.

    Returns:
        list[str]: Candidate variants in resolution order.
    """
    candidate = candidate.strip(" ,:;()[]{}")
    candidate_lower = candidate.lower()
    variants = [candidate]

    if candidate_lower.startswith("jenkins "):
        variants.append(candidate[8:].strip())

    if candidate_lower.endswith(" plugin"):
        variants.append(candidate[:-7].strip())

    if candidate_lower.startswith("jenkins ") and candidate_lower.endswith(" plugin"):
        variants.append(candidate[8:-7].strip())

    return list(dict.fromkeys(variant for variant in variants if variant))


def resolve_target_entity(
    text: str,
    plugin_aliases: dict[str, str],
) -> GraphEntity | None:
    """
    Resolve a target plugin entity from text after a relation phrase.

    Args:
        text (str): Sentence text after a relation trigger.
        plugin_aliases (dict[str, str]): Alias map built from plugin IDs.

    Returns:
        GraphEntity | None: Resolved target entity, if found.
    """
    tokens = TARGET_TOKEN_PATTERN.findall(text)
    max_length = min(len(tokens), MAX_TARGET_TOKENS)

    for start_index in range(min(MAX_TARGET_START_OFFSET + 1, len(tokens))):
        for end_index in range(max_length, start_index, -1):
            candidate = " ".join(tokens[start_index:end_index])
            for variant in build_candidate_variants(candidate):
                target_id = resolve_plugin_name(variant, plugin_aliases)
                if target_id and target_id not in SKIPPED_TARGET_PLUGIN_IDS:
                    return make_plugin_entity(target_id)

    return None


def extract_triples_from_sentence(
    source_entity: GraphEntity,
    sentence: str,
    chunk: dict,
    plugin_aliases: dict[str, str],
) -> list[Triple]:
    """
    Extract graph triples from one sentence span.

    Args:
        source_entity (GraphEntity): Canonical source plugin entity.
        sentence (str): Sentence to inspect.
        chunk (dict): Source chunk payload.
        plugin_aliases (dict[str, str]): Alias map built from plugin IDs.

    Returns:
        list[Triple]: Extracted triples for the sentence.
    """
    extracted_triples: list[Triple] = []

    for relation, confidence, pattern in RELATION_PATTERNS:
        for match in pattern.finditer(sentence):
            target_entity = resolve_target_entity(
                sentence[match.end():],
                plugin_aliases,
            )
            if not target_entity or target_entity.entity_id == source_entity.entity_id:
                continue

            extracted_triples.append(
                Triple(
                    source=source_entity,
                    relation=relation,
                    target=target_entity,
                    evidence=build_chunk_evidence(chunk, sentence),
                    confidence=confidence,
                )
            )

    return extracted_triples


def extract_triples_from_chunk(
    chunk: dict,
    plugin_aliases: dict[str, str],
) -> list[Triple]:
    """
    Extract graph triples from one plugin chunk.

    Args:
        chunk (dict): Chunk payload from chunks_plugin_docs.json.
        plugin_aliases (dict[str, str]): Alias map built from plugin IDs.

    Returns:
        list[Triple]: Validated triples found in the chunk.
    """
    metadata = chunk.get("metadata", {})
    source_title = metadata.get("title", "")
    source_plugin_id = resolve_plugin_name(source_title, plugin_aliases)
    if not source_plugin_id:
        return []

    source_entity = make_plugin_entity(source_plugin_id)

    extracted_triples: list[Triple] = []
    seen_triples = set()

    for sentence in sentence_split(chunk.get("chunk_text", "")):
        for triple in extract_triples_from_sentence(
            source_entity,
            sentence,
            chunk,
            plugin_aliases,
        ):
            triple_key = (
                triple.source.entity_id,
                triple.relation,
                triple.target.entity_id,
                triple.evidence.evidence,
            )
            if triple_key in seen_triples:
                continue
            seen_triples.add(triple_key)
            extracted_triples.append(triple)

    return extracted_triples


def extract_triples(
    chunks: list[dict],
    plugin_aliases: dict[str, str],
) -> list[Triple]:
    """
    Extract graph triples from plugin chunks.

    Args:
        chunks (list[dict]): Plugin documentation chunks.
        plugin_aliases (dict[str, str]): Alias map built from plugin IDs.

    Returns:
        list[Triple]: All validated triples found across chunks.
    """
    triples: list[Triple] = []

    for chunk in chunks:
        triples.extend(extract_triples_from_chunk(chunk, plugin_aliases))

    return triples
