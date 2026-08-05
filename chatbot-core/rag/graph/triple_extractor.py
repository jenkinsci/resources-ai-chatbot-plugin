"""Deterministic triple extraction for plugin graph chunks."""

import re
from collections.abc import Collection, Mapping

from rag.graph.models import GraphEntity, GraphEvidence, Triple
from rag.graph.schema import GraphEntityType, GraphRelationType


MAX_TARGET_TOKENS = 8
MAX_TARGET_SCAN_OFFSET = 8
MAX_TARGET_CONTEXT_TOKENS = MAX_TARGET_TOKENS + MAX_TARGET_SCAN_OFFSET
TARGET_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9+._-]*")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
CODE_BLOCK_PLACEHOLDER_PATTERN = re.compile(r"\[\[CODE_BLOCK_[^\]]+\]\]")
LIST_ENTRY_PATTERN = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
MARKDOWN_HEADING_PATTERN = re.compile(r"^#{1,6}\s+")
VERSION_HEADING_PATTERN = re.compile(
    r"^(?:version\s+|v?\d+\.\d+(?:\.\d+)*(?:\s|$))",
    re.IGNORECASE,
)
KNOWN_HEADING_PATTERN = re.compile(
    r"^(?:changelog|release notes?|version history|requirements?|"
    r"dependencies?|optional dependencies?)\s*:?$",
    re.IGNORECASE,
)
UNRESOLVED_SUBJECT_PATTERN = re.compile(r"^(?:it|they)\b", re.IGNORECASE)
CHANGELOG_HEADING_PATTERN = re.compile(
    r"^(?:changelog|release notes?|version history)\b",
    re.IGNORECASE,
)
VERSION_ENTRY_PATTERN = re.compile(
    r"^(?:version\s+)?v?\d+\.\d+(?:\.\d+)*(?:\s|$)",
    re.IGNORECASE,
)
RELEASE_ENTRY_PATTERN = re.compile(
    r"^(?:fix(?:ed)?|add(?:ed)?|remov(?:e|ed)|chang(?:e|ed)|"
    r"updat(?:e|ed)|correct(?:ed)?|improv(?:e|ed))\s*[:\-]",
    re.IGNORECASE,
)
JENKINS_ISSUE_PATTERN = re.compile(r"\bJENKINS-\d+\b", re.IGNORECASE)
SKIPPED_TARGET_PLUGIN_IDS = {"jenkins"}
RELATION_PATTERNS = (
    (
        GraphRelationType.OPTIONAL_DEPENDS_ON.value,
        re.compile(
            r"\b(?:optionally depends on|optional dependencies include|"
            r"optional dependency(?: is|:)?|optionally requires)\b",
            re.IGNORECASE,
        ),
    ),
    (
        GraphRelationType.DEPENDS_ON.value,
        re.compile(r"(?<!optionally )\bdepends on\b", re.IGNORECASE),
    ),
    (
        GraphRelationType.DEPENDS_ON.value,
        re.compile(r"(?<!optionally )\brequires?\b", re.IGNORECASE),
    ),
    (
        GraphRelationType.CONFLICTS_WITH.value,
        re.compile(r"\b(?:conflicts? with|incompatible with)\b", re.IGNORECASE),
    ),
)
PluginLookup = Mapping[str, tuple[str, ...]]


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
    Split documentation into sentence and structural spans.

    Args:
        text (str): Chunk text to split.

    Returns:
        list[str]: Non-empty sentences.
    """
    spans: list[str] = []
    for section in CODE_BLOCK_PLACEHOLDER_PATTERN.split(text.replace("\r\n", "\n")):
        spans.extend(_split_structural_section(section))
    return spans


def _split_structural_section(section: str) -> list[str]:
    """
    Split one non-code section while preserving soft line breaks.

    Args:
        section (str): Documentation section without code placeholders.

    Returns:
        list[str]: Non-empty sentence or structural spans.
    """
    spans: list[str] = []
    current_lines: list[str] = []

    def flush_lines() -> None:
        if not current_lines:
            return
        joined_text = " ".join(current_lines)
        spans.extend(
            sentence.strip()
            for sentence in SENTENCE_SPLIT_PATTERN.split(joined_text)
            if sentence.strip()
        )
        current_lines.clear()

    for line in section.split("\n"):
        stripped_line = line.strip()
        if not stripped_line:
            flush_lines()
            continue

        if _is_structural_line(stripped_line):
            flush_lines()
            list_text = LIST_ENTRY_PATTERN.sub("", stripped_line).strip()
            if list_text:
                spans.append(list_text)
            continue

        current_lines.append(stripped_line)

    flush_lines()
    return spans


def _is_structural_line(line: str) -> bool:
    """
    Identify headings and list entries that must not join adjacent text.

    Args:
        line (str): Trimmed documentation line.

    Returns:
        bool: True when the line starts a structural span.
    """
    return bool(
        LIST_ENTRY_PATTERN.match(line)
        or MARKDOWN_HEADING_PATTERN.match(line)
        or VERSION_HEADING_PATTERN.match(line)
        or KNOWN_HEADING_PATTERN.match(line)
    )


def build_candidate_variants(candidate: str) -> list[str]:
    """
    Build candidate name variants for alias lookup.

    Args:
        candidate (str): Raw plugin phrase from a sentence.

    Returns:
        list[str]: Candidate variants in resolution order.
    """
    candidate = candidate.strip(" .,!?;:()[]{}")
    candidate_lower = candidate.lower()
    variants = [candidate]

    if candidate_lower.startswith("jenkins "):
        variants.append(candidate[8:].strip())

    if candidate_lower.endswith(" plugin"):
        variants.append(candidate[:-7].strip())

    if candidate_lower.startswith("jenkins ") and candidate_lower.endswith(" plugin"):
        variants.append(candidate[8:-7].strip())

    return list(dict.fromkeys(variant for variant in variants if variant))


def build_plugin_lookup(plugin_ids: Collection[str]) -> dict[str, tuple[str, ...]]:
    """
    Build a reusable lookup from readable plugin forms to canonical IDs.

    Args:
        plugin_ids (Collection[str]): Canonical IDs from plugin_names.json.

    Returns:
        dict[str, tuple[str, ...]]: Deterministic readable-form lookup.
    """
    lookup: dict[str, list[str]] = {}
    for plugin_id in plugin_ids:
        plugin_forms = {
            plugin_id.lower(),
            re.sub(r"[-_]+", " ", plugin_id.lower()),
        }
        if plugin_id.endswith("-plugin"):
            base_name = plugin_id[:-7].lower()
            plugin_forms.update(
                {
                    base_name,
                    re.sub(r"[-_]+", " ", base_name),
                }
            )
        for plugin_form in plugin_forms:
            if plugin_id not in lookup.setdefault(plugin_form, []):
                lookup[plugin_form].append(plugin_id)

    return {plugin_form: tuple(ids) for plugin_form, ids in lookup.items()}


def resolve_plugin_id(
    candidate: str,
    plugin_lookup: PluginLookup,
    require_explicit_plugin_word: bool = False,
) -> str | None:
    """
    Resolve a documentation phrase against canonical plugin IDs.

    Matching is derived from the canonical ID itself. Hyphens and underscores
    can be written as spaces, and common Jenkins documentation prefixes and
    suffixes are accepted without a manually maintained alias table.

    Args:
        candidate (str): Candidate plugin phrase from documentation.
        plugin_lookup (PluginLookup): Readable forms mapped to canonical IDs.
        require_explicit_plugin_word (bool): Require the word Plugin for
            single-word target IDs.

    Returns:
        str | None: Matching canonical ID, if one exists.
    """
    candidate_key = re.sub(r"\s+", " ", candidate.strip().lower())
    if not candidate_key:
        return None

    candidate_forms = [candidate_key]
    if candidate_key.startswith("jenkins "):
        candidate_forms.append(candidate_key[8:].strip())
    candidate_forms.extend(
        form[:-7].strip()
        for form in tuple(candidate_forms)
        if form.endswith(" plugin")
    )

    for candidate_form in candidate_forms:
        for plugin_id in plugin_lookup.get(candidate_form, ()):
            if require_explicit_plugin_word and "plugin" not in candidate_key.split():
                continue
            return plugin_id

    return None


def resolve_target_entities(
    text: str,
    plugin_lookup: PluginLookup,
    scan_from_end: bool = False,
) -> list[GraphEntity]:
    """
    Resolve target plugin entities from a relation text span.

    Args:
        text (str): Sentence text after a relation trigger.
        plugin_lookup (PluginLookup): Readable forms mapped to canonical IDs.
        scan_from_end (bool): Search from the end when resolving target-before
            relation wording while preserving all non-overlapping targets.

    Returns:
        list[GraphEntity]: Resolved target entities in text order.
    """
    tokens = TARGET_TOKEN_PATTERN.findall(text)
    if scan_from_end:
        tokens = tokens[-MAX_TARGET_CONTEXT_TOKENS:]
    else:
        tokens = tokens[:MAX_TARGET_CONTEXT_TOKENS]
    target_entities: list[tuple[int, GraphEntity]] = []
    seen_target_ids = set()
    consumed_until = 0

    start_indices = range(min(MAX_TARGET_SCAN_OFFSET + 1, len(tokens)))
    if scan_from_end:
        start_indices = range(len(tokens) - 1, -1, -1)

    for start_index in start_indices:
        if not scan_from_end and start_index < consumed_until:
            continue
        max_end_index = min(len(tokens), start_index + MAX_TARGET_TOKENS)
        found_target_at_start = False
        for end_index in range(max_end_index, start_index, -1):
            candidate = " ".join(tokens[start_index:end_index])
            for variant in build_candidate_variants(candidate):
                plugin_id = resolve_plugin_id(
                    variant,
                    plugin_lookup,
                    require_explicit_plugin_word=True,
                )
                if not plugin_id or plugin_id in SKIPPED_TARGET_PLUGIN_IDS:
                    continue
                if plugin_id in seen_target_ids:
                    continue

                target_entities.append(
                    (start_index, make_plugin_entity(plugin_id))
                )
                seen_target_ids.add(plugin_id)
                consumed_until = end_index
                found_target_at_start = True
                break
            if found_target_at_start:
                break

    if scan_from_end:
        target_entities.reverse()

    return [target for _, target in target_entities]


def should_skip_target(
    source_entity: GraphEntity,
    target_entity: GraphEntity,
) -> bool:
    """
    Check whether a resolved target should be rejected for this sentence.

    Args:
        source_entity (GraphEntity): Source plugin entity.
        target_entity (GraphEntity): Target plugin entity.

    Returns:
        bool: True when the target should not become a triple.
    """
    return (
        target_entity.entity_id == source_entity.entity_id
    )


def has_valid_relation_subject(sentence: str, relation_start: int) -> bool:
    """
    Reject relation phrases introduced by unresolved pronouns.

    Args:
        sentence (str): Sentence containing the relation phrase.
        relation_start (int): Start offset of the relation phrase.

    Returns:
        bool: False when the relation subject is unresolved.
    """
    subject = sentence[:relation_start].strip()
    return not UNRESOLVED_SUBJECT_PATTERN.match(subject)


def is_changelog_span(text: str) -> bool:
    """
    Identify spans that describe historical release changes.

    Args:
        text (str): Documentation span containing a possible relation.

    Returns:
        bool: True when strong changelog signals are present.
    """
    normalized_text = text.strip()
    issue_count = len(JENKINS_ISSUE_PATTERN.findall(normalized_text))
    return bool(
        CHANGELOG_HEADING_PATTERN.match(normalized_text)
        or VERSION_ENTRY_PATTERN.match(normalized_text)
        or RELEASE_ENTRY_PATTERN.match(normalized_text)
        or issue_count >= 2
    )


def extract_triples_from_sentence(
    source_entity: GraphEntity,
    sentence: str,
    chunk: dict,
    plugin_lookup: PluginLookup,
    preceding_text: str = "",
) -> list[Triple]:
    """
    Extract graph triples from one sentence span.

    Args:
        source_entity (GraphEntity): Canonical source plugin entity.
        sentence (str): Sentence to inspect.
        chunk (dict): Source chunk payload.
        plugin_lookup (PluginLookup): Readable forms mapped to canonical IDs.
        preceding_text (str): Previous sentence used for optional dependency
            target resolution when the current sentence omits the target.

    Returns:
        list[Triple]: Extracted triples for the sentence.
    """
    extracted_triples: list[Triple] = []

    if is_changelog_span(sentence):
        return extracted_triples

    for relation, pattern in RELATION_PATTERNS:
        for match in pattern.finditer(sentence):
            if not has_valid_relation_subject(sentence, match.start()):
                continue

            evidence_text = sentence
            target_entities = resolve_target_entities(
                sentence[match.end():],
                plugin_lookup,
            )
            if not target_entities and relation == GraphRelationType.OPTIONAL_DEPENDS_ON.value:
                target_entities = resolve_target_entities(
                    sentence[:match.start()],
                    plugin_lookup,
                    scan_from_end=True,
                )
                if not target_entities and preceding_text:
                    target_entities = resolve_target_entities(
                        preceding_text,
                        plugin_lookup,
                        scan_from_end=True,
                    )
                    if target_entities:
                        evidence_text = f"{preceding_text.strip()} {sentence.strip()}"

            for target_entity in target_entities:
                if should_skip_target(source_entity, target_entity):
                    continue

                extracted_triples.append(
                    Triple(
                        source=source_entity,
                        relation=relation,
                        target=target_entity,
                        evidence=build_chunk_evidence(chunk, evidence_text),
                    )
                )

    return extracted_triples


def _extract_triples_from_chunk(
    chunk: dict,
    plugin_lookup: PluginLookup,
) -> list[Triple]:
    """
    Extract graph triples from one plugin chunk.

    Args:
        chunk (dict): Chunk payload from chunks_plugin_docs.json.
        plugin_lookup (PluginLookup): Readable forms mapped to canonical IDs.

    Returns:
        list[Triple]: Validated triples found in the chunk.
    """
    metadata = chunk.get("metadata", {})
    source_title = metadata.get("title", "")
    source_plugin_id = resolve_plugin_id(source_title, plugin_lookup)
    if not source_plugin_id:
        return []

    source_entity = make_plugin_entity(source_plugin_id)

    extracted_triples: list[Triple] = []
    seen_triples = set()

    previous_sentence = ""
    for sentence in sentence_split(chunk.get("chunk_text", "")):
        for triple in extract_triples_from_sentence(
            source_entity,
            sentence,
            chunk,
            plugin_lookup,
            previous_sentence,
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
        previous_sentence = sentence

    return extracted_triples


def extract_triples_from_chunk(
    chunk: dict,
    plugin_ids: Collection[str],
) -> list[Triple]:
    """
    Extract triples from one chunk using canonical plugin IDs.

    Args:
        chunk (dict): Chunk payload from chunks_plugin_docs.json.
        plugin_ids (Collection[str]): Canonical IDs from plugin_names.json.

    Returns:
        list[Triple]: Validated triples found in the chunk.
    """
    return _extract_triples_from_chunk(chunk, build_plugin_lookup(plugin_ids))


def extract_triples(
    chunks: list[dict],
    plugin_ids: Collection[str],
) -> list[Triple]:
    """
    Extract graph triples from plugin chunks.

    Args:
        chunks (list[dict]): Plugin documentation chunks.
        plugin_ids (Collection[str]): Canonical IDs from plugin_names.json.

    Returns:
        list[Triple]: All validated triples found across chunks.
    """
    plugin_lookup = build_plugin_lookup(plugin_ids)
    best_triples: dict[tuple[str, str, str], Triple] = {}

    for chunk in chunks:
        for triple in _extract_triples_from_chunk(chunk, plugin_lookup):
            triple_key = (
                triple.source.entity_id,
                triple.relation,
                triple.target.entity_id,
            )
            current_triple = best_triples.get(triple_key)
            if current_triple is None or _is_preferred_triple(triple, current_triple):
                best_triples[triple_key] = triple

    return list(best_triples.values())


def _is_preferred_triple(candidate: Triple, current: Triple) -> bool:
    """
    Compare duplicate relationships using deterministic evidence preferences.

    Args:
        candidate (Triple): New candidate relationship.
        current (Triple): Relationship currently selected for the key.

    Returns:
        bool: True when the candidate should replace the current triple.
    """
    candidate_has_plugin_word = "plugin" in candidate.evidence.evidence.lower()
    current_has_plugin_word = "plugin" in current.evidence.evidence.lower()
    if candidate_has_plugin_word != current_has_plugin_word:
        return candidate_has_plugin_word

    if len(candidate.evidence.evidence) != len(current.evidence.evidence):
        return len(candidate.evidence.evidence) < len(current.evidence.evidence)

    return candidate.evidence.source_chunk_id < current.evidence.source_chunk_id
