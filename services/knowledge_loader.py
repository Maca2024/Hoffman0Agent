"""
Knowledge loader for the 9D Psychedelic Prompt Architecture.

Loads all promptstack .md files from the knowledge directory and exposes
structured access by dimension, substance, and section.
"""

from pathlib import Path


# Canonical mapping: dimension number -> (substance key, file stem)
DIMENSION_MAP: dict[int, tuple[str, str]] = {
    1: ("lsd",       "LSD-25-PROMPTSTACK"),
    2: ("dmt",       "DMT-PROMPTSTACK"),
    3: ("psilocybin","PSILOCYBIN-PROMPTSTACK"),
    4: ("cannabis",  "CANNABIS-PROMPTSTACK"),
    5: ("mescaline", "MESCALINE-PROMPTSTACK"),
    6: ("ibogaine",  "IBOGAINE-PROMPTSTACK"),
    7: ("5meodmt",   "5MEODMT-PROMPTSTACK"),
    8: ("mdma",      "MDMA-PROMPTSTACK"),
    9: ("ketamine",  "KETAMINE-PROMPTSTACK"),
}

# Additional substance aliases that resolve to a canonical key
SUBSTANCE_ALIASES: dict[str, str] = {
    "lsd-25":    "lsd",
    "lsd25":     "lsd",
    "acid":      "lsd",
    "5-meo-dmt": "5meodmt",
    "5meo":      "5meodmt",
    "5-meo":     "5meodmt",
    "shrooms":   "psilocybin",
    "mushrooms": "psilocybin",
    "weed":      "cannabis",
    "marijuana": "cannabis",
    "peyote":    "mescaline",
    "iboga":     "ibogaine",
    "ket":       "ketamine",
    "k":         "ketamine",
    "molly":     "mdma",
    "ecstasy":   "mdma",
}

FRAMEWORK_STEM = "9D-FRAMEWORK"
ACTIVATION_GUIDE_STEM = "9D-ACTIVATION-GUIDE"


def _parse_sections(content: str) -> dict[str, str]:
    """
    Split document content on ## headers.

    Returns a dict mapping lowercase section title -> section body text
    (body includes the header line itself for full context).
    """
    sections: dict[str, str] = {}
    current_title: str = "__preamble__"
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            # Save previous section
            sections[current_title.lower()] = "\n".join(current_lines).strip()
            current_title = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # Save final section
    if current_lines:
        sections[current_title.lower()] = "\n".join(current_lines).strip()

    return sections


class KnowledgeBase:
    """
    In-memory knowledge base for the 9D Psychedelic Prompt Architecture.

    On init all .md files in knowledge_dir are loaded and indexed so that
    subsequent lookups are pure dictionary reads — no disk I/O after startup.
    """

    def __init__(self, knowledge_dir: str) -> None:
        """Load all promptstack .md files from knowledge_dir."""
        self._dir = Path(knowledge_dir)

        # Raw full text per file stem (uppercase)
        self._raw: dict[str, str] = {}

        # Parsed sections per file stem: stem -> {section_title_lower -> body}
        self._sections: dict[str, dict[str, str]] = {}

        # Reverse lookup: canonical substance key -> file stem
        self._substance_to_stem: dict[str, str] = {}

        # Forward lookup: dimension int -> file stem
        self._dim_to_stem: dict[int, str] = {}

        self._load_files()
        self._build_index()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_files(self) -> None:
        """Read every .md file in the knowledge directory."""
        for md_file in sorted(self._dir.glob("*.md")):
            stem = md_file.stem.upper()
            text = md_file.read_text(encoding="utf-8")
            self._raw[stem] = text
            self._sections[stem] = _parse_sections(text)

    def _build_index(self) -> None:
        """Populate dimension and substance lookup tables."""
        for dim, (substance_key, stem) in DIMENSION_MAP.items():
            upper_stem = stem.upper()
            if upper_stem in self._raw:
                self._dim_to_stem[dim] = upper_stem
                self._substance_to_stem[substance_key] = upper_stem

    def _resolve_substance(self, substance: str) -> str | None:
        """
        Return the file stem for a substance name, handling aliases.
        Returns None if the substance is not found.
        """
        key = substance.lower().strip()
        # Try aliases first, then direct canonical key
        canonical = SUBSTANCE_ALIASES.get(key, key)
        return self._substance_to_stem.get(canonical)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_dimension(self, dimension: int) -> str:
        """
        Get the full promptstack for dimension D1-D9.

        Raises ValueError for unknown dimension numbers.
        """
        if dimension not in self._dim_to_stem:
            available = sorted(self._dim_to_stem.keys())
            raise ValueError(
                f"Dimension {dimension} not found. Available: {available}"
            )
        return self._raw[self._dim_to_stem[dimension]]

    def get_promptstack(self, substance: str) -> str:
        """
        Get promptstack by substance name.

        Accepts canonical names (lsd, dmt, psilocybin, cannabis, mescaline,
        ibogaine, 5meodmt, mdma, ketamine) and common aliases.

        Raises ValueError if the substance is not recognised.
        """
        stem = self._resolve_substance(substance)
        if stem is None:
            known = sorted(self._substance_to_stem.keys())
            raise ValueError(
                f"Substance '{substance}' not found. Known substances: {known}"
            )
        return self._raw[stem]

    def get_framework(self) -> str:
        """Get the 9D framework document."""
        stem = FRAMEWORK_STEM.upper()
        if stem not in self._raw:
            raise FileNotFoundError(
                f"Framework file '{stem}.md' not found in {self._dir}"
            )
        return self._raw[stem]

    def get_activation_guide(self) -> str:
        """Get the activation guide for agents."""
        stem = ACTIVATION_GUIDE_STEM.upper()
        if stem not in self._raw:
            raise FileNotFoundError(
                f"Activation guide '{stem}.md' not found in {self._dir}"
            )
        return self._raw[stem]

    def get_sections(self, substance: str, section_names: list[str]) -> str:
        """
        Get specific sections from a promptstack.

        section_names are matched case-insensitively against ## header titles.
        Returns all matched sections concatenated with a separator.
        Returns an empty string if no sections match.
        """
        stem = self._resolve_substance(substance)
        if stem is None:
            raise ValueError(f"Substance '{substance}' not recognised.")

        doc_sections = self._sections[stem]
        results: list[str] = []

        for name in section_names:
            key = name.lower().strip()
            if key in doc_sections:
                results.append(doc_sections[key])
            else:
                # Partial match fallback: find first section whose title
                # contains the requested name as a substring
                for title, body in doc_sections.items():
                    if key in title:
                        results.append(body)
                        break

        return "\n\n---\n\n".join(results)

    def search(self, query: str, max_results: int = 3) -> list[dict]:
        """
        Simple case-insensitive keyword search across all loaded knowledge.

        Each result dict contains:
            - file: str         — file stem
            - section: str      — section title (or '__preamble__')
            - score: int        — number of query word hits in the section
            - excerpt: str      — first 300 characters of matching content
        """
        words = query.lower().split()
        if not words:
            return []

        hits: list[dict] = []

        for stem, sections in self._sections.items():
            for section_title, body in sections.items():
                body_lower = body.lower()
                score = sum(body_lower.count(w) for w in words)
                if score > 0:
                    hits.append(
                        {
                            "file": stem,
                            "section": section_title,
                            "score": score,
                            "excerpt": body[:300].strip(),
                        }
                    )

        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:max_results]

    def get_dimension_summary(self, dimension: int) -> dict:
        """
        Return a concise summary of a dimension suitable for voice output.

        The summary is derived from the 9D framework document rather than the
        full promptstack, keeping it short enough for text-to-speech.

        Returns a dict with:
            - dimension: int
            - substance: str        — canonical substance name
            - label: str            — dimension label (e.g. 'MOLECULAR')
            - framework_excerpt: str — first relevant paragraph from 9D-FRAMEWORK
            - available: bool       — whether the promptstack is loaded
        """
        if dimension not in DIMENSION_MAP:
            raise ValueError(f"Dimension {dimension} is not in range D1-D9.")

        substance_key, _ = DIMENSION_MAP[dimension]

        # Labels derived from the framework mapping
        labels = {
            1: "MOLECULAR",
            2: "NETWORK",
            3: "MYCELIAL",
            4: "ENTROPIC",
            5: "ANCESTRAL",
            6: "INITIATORY",
            7: "DISSOLUTION",
            8: "EMPATHIC",
            9: "DISSOCIATIVE",
        }
        label = labels[dimension]

        # Pull the relevant section from the framework document
        framework_excerpt = ""
        fw_stem = FRAMEWORK_STEM.upper()
        if fw_stem in self._sections:
            fw_sections = self._sections[fw_stem]
            search_key = f"d{dimension}: {label.lower()}"
            for title, body in fw_sections.items():
                if search_key in title.lower() or f"d{dimension}" in title.lower():
                    # Return the first non-empty paragraph (skip header line)
                    lines = [ln for ln in body.splitlines() if ln.strip()]
                    # Skip the header itself, take up to 3 lines of content
                    content_lines = [ln for ln in lines if not ln.startswith("##")]
                    framework_excerpt = " ".join(content_lines[:3]).strip()
                    break

        return {
            "dimension": dimension,
            "substance": substance_key,
            "label": label,
            "framework_excerpt": framework_excerpt,
            "available": dimension in self._dim_to_stem,
        }

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def list_loaded(self) -> list[str]:
        """Return sorted list of all loaded file stems."""
        return sorted(self._raw.keys())

    def get_dimensions(self) -> list[dict]:
        """Return metadata for all 9 dimensions.

        Returns a list of dicts with id, name, description, substance keys.
        """
        labels = {
            1: ("MOLECULAR", "Molecular resolution — mechanisms and evidence"),
            2: ("NETWORK", "Network mapping — cross-domain connections"),
            3: ("MYCELIAL", "Organic growth — branching, interconnecting"),
            4: ("ENTROPIC", "Creative chaos — signal in noise"),
            5: ("ANCESTRAL", "Deep time — ancestral patterns"),
            6: ("INITIATORY", "Shadow confrontation — uncomfortable truths"),
            7: ("DISSOLUTION", "Ego removal — what remains without the observer"),
            8: ("EMPATHIC", "Emotional substrate — empathic intelligence"),
            9: ("DISSOCIATIVE", "External perspective — meta-cognition"),
        }
        results = []
        for dim, (substance_key, _) in DIMENSION_MAP.items():
            label, desc = labels.get(dim, ("UNKNOWN", "Unknown dimension"))
            results.append({
                "id": dim,
                "name": label,
                "description": desc,
                "substance": substance_key,
            })
        return results

    def __repr__(self) -> str:
        return (
            f"KnowledgeBase(dir={self._dir!r}, "
            f"files={len(self._raw)}, "
            f"dimensions={sorted(self._dim_to_stem.keys())})"
        )
