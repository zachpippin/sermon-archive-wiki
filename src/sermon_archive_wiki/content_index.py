from __future__ import annotations

from collections import Counter
import math
import re
import textwrap

from .models import SermonRecord, merge_unique
from .util import page_stem


WORD_RE = re.compile(r"[a-z][a-z']{2,}")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
SUMMARY_SKIP_PHRASES = (
    "all right",
    "before i read",
    "grab a bible",
    "heavenly father",
    "if you have a bible",
    "if you will grab",
    "i'm going to pray",
    "last week",
    "let me just recap",
    "my name is",
    "open up your bibles",
    "turn to",
    "we are back",
    "we're going to be",
    "we're going to look",
    "we're going to read",
    "we've labeled it",
    "welcome",
    "you should be excited",
)
SUMMARY_SIGNAL_PHRASES = (
    "the point",
    "main point",
    "what we see",
    "what's wonderful",
    "the picture",
    "that means",
    "there is a day coming",
    "the sermon calls",
    "the passage shows",
    "we should",
    "we need",
    "my hope",
    "hope is",
    "restoration",
    "eternity",
    "gospel",
    "kingdom",
    "peace",
    "glory",
)
STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "because",
    "been",
    "before",
    "being",
    "between",
    "church",
    "could",
    "does",
    "doing",
    "down",
    "each",
    "even",
    "every",
    "from",
    "going",
    "good",
    "have",
    "here",
    "into",
    "just",
    "know",
    "like",
    "look",
    "make",
    "many",
    "more",
    "most",
    "much",
    "need",
    "only",
    "other",
    "over",
    "people",
    "really",
    "right",
    "said",
    "same",
    "sermon",
    "should",
    "some",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "thing",
    "things",
    "this",
    "those",
    "through",
    "time",
    "want",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "will",
    "with",
    "would",
    "your",
}
THEME_RULES = {
    "Gospel": ("gospel", "cross", "resurrection", "atonement", "good news"),
    "Grace": ("grace", "mercy", "forgive", "forgiveness"),
    "Discipleship": ("disciple", "follow jesus", "obedience", "formation"),
    "Mission": ("mission", "evangel", "nations", "sent", "witness"),
    "Prayer": ("pray", "prays", "praying", "prayer", "intercede", "lament"),
    "Scripture": ("scripture", "bible", "word of god"),
    "Church": ("church membership", "body of christ", "members", "elders", "deacons"),
    "Worship": ("worship", "praise", "glory", "sing"),
    "Wisdom": ("wisdom", "wise", "fool", "proverbs"),
    "Suffering": ("suffer", "suffering", "pain", "grief", "trial"),
    "Holiness": ("holy", "holiness", "sanctification", "repent"),
    "Justice and Mercy": ("justice", "mercy", "poor", "oppressed", "neighbor"),
    "Marriage and Family": ("marriage", "husband", "wife", "parenting", "family"),
    "Generosity": ("generous", "generosity", "money", "giving", "steward", "treasure"),
    "Identity in Christ": ("identity", "in christ", "adoption", "beloved"),
    "Eschatology": ("second coming", "day of the lord", "kingdom of god", "kingdom of heaven", "revelation", "eternity"),
    "Holy Spirit": ("holy spirit", "spirit", "pentecost"),
}
TOPIC_RULES = {
    "Faith": ("faith", "believe", "trust"),
    "Hope": ("hope", "future", "promise"),
    "Love": ("love", "beloved", "neighbor"),
    "Repentance": ("repent", "repentance", "confess"),
    "Idolatry": ("idol", "idolatry", "false god"),
    "Anxiety and Fear": ("anxiety", "anxious", "fear", "afraid"),
    "Spiritual Warfare": ("warfare", "armor", "enemy", "satan"),
    "Leadership": ("leader", "elder", "shepherd", "pastor"),
    "Community": ("community", "one another", "small group"),
    "Work and Rest": ("workplace", "vocation", "labor", "sabbath", "rest"),
    "Hospitality": ("hospitality", "welcome", "stranger"),
    "Sexual Ethics": ("sex", "sexual", "desire", "purity"),
    "Money": ("money", "wealth", "rich", "treasure"),
    "Parenting": ("parenting", "parents", "our children", "your children", "kids"),
    "Forgiveness": ("forgive", "forgiveness", "reconcile"),
}


def apply_content_index(
    records: list[SermonRecord],
    max_related_sermons: int = 5,
    summary_sentences: int = 3,
) -> list[SermonRecord]:
    """Generate local review summaries, topic labels, and related-sermon links."""
    documents = [document_counter(record) for record in records]
    document_frequency = Counter(term for document in documents for term in document)
    vectors = [weighted_vector(document, document_frequency, len(records)) for document in documents]
    norms = [vector_norm(vector) for vector in vectors]

    for index, record in enumerate(records):
        if not record.transcript_text.strip():
            continue
        if not record.generated_summary.strip():
            summary = extractive_summary(record, document_frequency, len(records), summary_sentences)
            if summary:
                record.generated_summary = summary
                record.summary_status = "deterministic_review_required"
                record.summary_source = "deterministic_content_index"
        if record.summary_source != "external_command":
            themes, topics = infer_content_labels(record)
            record.themes = merge_unique(record.themes, themes)
            record.topics = merge_unique(record.topics, topics)
        if record.generated_summary and record.summary_source != "external_command":
            append_unique(record.review_flags, "Generated content summary/themes were added locally; review before relying on them.")

    if max_related_sermons > 0:
        for index, record in enumerate(records):
            related = related_records(index, records, vectors, norms, max_related_sermons)
            record.related_sermons = merge_unique(record.related_sermons, [related_label(item) for item in related])
    return records


def extractive_summary(record: SermonRecord, document_frequency: Counter[str], document_count: int, sentence_count: int) -> str:
    sentences = [clean_sentence(sentence) for sentence in SENTENCE_RE.split(record.transcript_text)]
    prefix = summary_prefix(record)
    candidates = [
        (position, sentence)
        for position, sentence in enumerate(sentences)
        if is_summary_candidate(sentence)
    ]
    if not candidates:
        return " ".join(part for part in (prefix, fallback_summary(record.transcript_text)) if part).strip()
    title_terms = set(tokens(" ".join([record.title, record.series, " ".join(record.scripture_refs)])))
    scored: list[tuple[float, int, str]] = []
    for position, sentence in candidates[:900]:
        sentence_tokens = tokens(sentence)
        if not sentence_tokens:
            continue
        score = sum(inverse_document_frequency(term, document_frequency, document_count) for term in sentence_tokens)
        score /= math.sqrt(len(sentence_tokens))
        if title_terms.intersection(sentence_tokens):
            score *= 1.08
        score *= summary_quality_multiplier(sentence, position)
        scored.append((score, position, sentence))
    selected = select_diverse_sentences(scored, max(1, sentence_count))
    summary = " ".join(sentence for _score, _position, sentence in selected)
    summary = " ".join(part for part in (prefix, "Generated review summary:", summary) if part)
    summary = re.sub(r"\s+", " ", summary).strip()
    return textwrap.shorten(summary, width=950, placeholder="...")


def is_summary_candidate(sentence: str) -> bool:
    lowered = sentence.casefold()
    if not 55 <= len(sentence) <= 420:
        return False
    if len(tokens(sentence)) < 8:
        return False
    if any(phrase in lowered for phrase in SUMMARY_SKIP_PHRASES):
        return False
    return True


def summary_quality_multiplier(sentence: str, position: int) -> float:
    lowered = sentence.casefold()
    multiplier = 1.0
    if position < 6:
        multiplier *= 0.55
    if any(phrase in lowered for phrase in SUMMARY_SIGNAL_PHRASES):
        multiplier *= 1.35
    if " uh " in f" {lowered} " or " um " in f" {lowered} ":
        multiplier *= 0.78
    if lowered.count(" i ") + lowered.count(" me ") + lowered.count(" my ") >= 4:
        multiplier *= 0.82
    if len(sentence) > 320:
        multiplier *= 0.78
    return multiplier


def select_diverse_sentences(scored: list[tuple[float, int, str]], limit: int) -> list[tuple[float, int, str]]:
    selected: list[tuple[float, int, str]] = []
    selected_terms: list[set[str]] = []
    for score, position, sentence in sorted(scored, reverse=True):
        current_terms = set(tokens(sentence))
        if any(jaccard_similarity(current_terms, terms) > 0.45 for terms in selected_terms):
            continue
        selected.append((score, position, sentence))
        selected_terms.append(current_terms)
        if len(selected) >= limit:
            break
    return sorted(selected, key=lambda item: item[1])


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def infer_content_labels(record: SermonRecord) -> tuple[list[str], list[str]]:
    metadata = " ".join([record.title, record.series, " ".join(record.scripture_refs)]).casefold()
    early = record.transcript_text[:5000].casefold()
    full = record.transcript_text.casefold()
    themes = ranked_labels(metadata, early, full, THEME_RULES, minimum=4)[:6]
    topics = ranked_labels(metadata, early, full, TOPIC_RULES, minimum=4)[:8]
    return themes, topics


def summary_prefix(record: SermonRecord) -> str:
    parts: list[str] = []
    if record.scripture_refs:
        parts.append("Primary text: " + ", ".join(record.scripture_refs[:3]) + ".")
    if record.series and record.series.casefold() not in record.title.casefold():
        parts.append(f"Series: {record.series}.")
    return " ".join(parts)


def fallback_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    return textwrap.shorten(cleaned, width=520, placeholder="...")


def ranked_labels(metadata: str, early: str, full: str, rules: dict[str, tuple[str, ...]], minimum: int) -> list[str]:
    scored: list[tuple[int, str]] = []
    for label, keywords in rules.items():
        score = 0
        for keyword in keywords:
            pattern = rf"\b{re.escape(keyword.casefold())}\b"
            score += len(re.findall(pattern, metadata)) * 8
            score += len(re.findall(pattern, early)) * 3
            score += len(re.findall(pattern, full))
        label_minimum = noisy_label_minimum(label, minimum)
        if score >= label_minimum:
            scored.append((score, label))
    return [label for _score, label in sorted(scored, key=lambda item: (-item[0], item[1]))]


def noisy_label_minimum(label: str, default: int) -> int:
    noisy = {
        "Marriage and Family": 12,
        "Parenting": 12,
        "Love": 8,
        "Money": 8,
    }
    return noisy.get(label, default)


def related_records(
    index: int,
    records: list[SermonRecord],
    vectors: list[dict[str, float]],
    norms: list[float],
    limit: int,
) -> list[SermonRecord]:
    current = records[index]
    scores: list[tuple[float, int, SermonRecord]] = []
    current_refs = {ref.casefold() for ref in [*current.scripture_refs, *current.mentioned_scripture_refs]}
    current_labels = {label.casefold() for label in [*current.topics, *current.themes]}
    for other_index, other in enumerate(records):
        if other_index == index:
            continue
        score = cosine_similarity(vectors[index], vectors[other_index], norms[index], norms[other_index])
        other_refs = {ref.casefold() for ref in [*other.scripture_refs, *other.mentioned_scripture_refs]}
        other_labels = {label.casefold() for label in [*other.topics, *other.themes]}
        if current.series and current.series.casefold() == other.series.casefold():
            score += 0.05
        if current_refs.intersection(other_refs):
            score += min(0.08, 0.02 * len(current_refs.intersection(other_refs)))
        if current_labels.intersection(other_labels):
            score += min(0.08, 0.02 * len(current_labels.intersection(other_labels)))
        if score >= 0.12:
            scores.append((score, -other_index, other))
    return [record for _score, _order, record in sorted(scores, reverse=True)[:limit]]


def cosine_similarity(left: dict[str, float], right: dict[str, float], left_norm: float, right_norm: float) -> float:
    if not left or not right or not left_norm or not right_norm:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    dot = sum(weight * right.get(term, 0.0) for term, weight in left.items())
    return dot / (left_norm * right_norm) if dot else 0.0


def document_counter(record: SermonRecord) -> Counter[str]:
    text = " ".join([record.title, record.series, " ".join(record.scripture_refs), record.transcript_text])
    return Counter(tokens(text))


def weighted_vector(document: Counter[str], document_frequency: Counter[str], document_count: int) -> dict[str, float]:
    weighted = {
        term: (1.0 + math.log(count)) * inverse_document_frequency(term, document_frequency, document_count)
        for term, count in document.items()
    }
    return dict(sorted(weighted.items(), key=lambda item: item[1], reverse=True)[:180])


def inverse_document_frequency(term: str, document_frequency: Counter[str], document_count: int) -> float:
    return math.log((1 + document_count) / (1 + document_frequency.get(term, 0))) + 1.0


def vector_norm(vector: dict[str, float]) -> float:
    return math.sqrt(sum(value * value for value in vector.values()))


def tokens(text: str) -> list[str]:
    result: list[str] = []
    for match in WORD_RE.finditer(text.casefold()):
        word = match.group(0).strip("'")
        if len(word) < 3 or word in STOPWORDS:
            continue
        result.append(normalize_token(word))
    return result


def normalize_token(word: str) -> str:
    if len(word) > 5 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 5 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 4 and word.endswith("ed"):
        return word[:-2]
    if len(word) > 4 and word.endswith("s"):
        return word[:-1]
    return word


def clean_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence).strip()


def related_label(record: SermonRecord) -> str:
    return page_stem(record.date, record.title)


def append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)
