# Phase 4: Summary Quality Improvements - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 04-summary-quality-improvements
**Areas discussed:** Reply/thread context, Enriched metadata, System prompt tuning, Model selection

---

## Reply/Thread Context

### Reply representation
| Option | Description | Selected |
|--------|-------------|----------|
| Inline reply snippet | Prepend short snippet of replied-to message | |
| Thread-style indentation | Group reply chains with indentation markers | |
| You decide | Claude picks best approach | |

**User's choice:** Thread-style indentation, plus: @here messages included in full, popular messages (via reactions/replies) highlighted
**Notes:** User combined multiple concerns into one answer — wants indentation AND importance signals baked into the reply handling

### Discord thread inclusion
| Option | Description | Selected |
|--------|-------------|----------|
| Include threads inline | Fetch thread messages alongside channel messages | |
| Separate thread summaries | Summarize each thread independently | |
| Skip threads | Only summarize top-level channel messages | ✓ |

**User's choice:** Skip threads
**Notes:** None

### Popularity threshold
| Option | Description | Selected |
|--------|-------------|----------|
| 3+ reactions or 3+ replies | Low bar for smaller servers | |
| 5+ reactions or 5+ replies | Medium bar for active servers | ✓ |
| You decide | Claude picks reasonable default | |

**User's choice:** 5+ reactions or 5+ replies
**Notes:** None

### @here/@everyone handling
| Option | Description | Selected |
|--------|-------------|----------|
| Always include verbatim | LLM must include full text in summary output | ✓ |
| Weight as important | Mark important but let LLM decide format | |

**User's choice:** Always include verbatim
**Notes:** None

### Reply nesting depth
| Option | Description | Selected |
|--------|-------------|----------|
| 2 levels max | Direct reply indented, deeper replies flatten | |
| Unlimited nesting | Full reply chain depth | |
| You decide | Claude picks based on LLM capabilities | ✓ |

**User's choice:** You decide
**Notes:** None

---

## Enriched Metadata

### Attachment representation
| Option | Description | Selected |
|--------|-------------|----------|
| Type + filename | [image: screenshot.png] format | ✓ |
| Type only | [image], [video], [file] format | |
| Keep as-is | Keep current [attachment] marker | |

**User's choice:** Type + filename
**Notes:** None

### Reaction counts
| Option | Description | Selected |
|--------|-------------|----------|
| Total count only | [12 reactions] on popular messages | ✓ |
| Top 3 emoji breakdown | Emoji-specific counts | |
| You decide | Claude picks | |

**User's choice:** Total count only
**Notes:** None

### Pinned messages
| Option | Description | Selected |
|--------|-------------|----------|
| Flag pinned messages | Add [PINNED] marker | |
| Skip pins | No special treatment | ✓ |

**User's choice:** Skip pins
**Notes:** None

### Embed content
| Option | Description | Selected |
|--------|-------------|----------|
| Include embed titles/descriptions | Extract title + description from embeds | ✓ |
| Skip embeds | Keep ignoring embeds | |

**User's choice:** Include embed titles/descriptions
**Notes:** None

### Embed scope
| Option | Description | Selected |
|--------|-------------|----------|
| User embeds only | Only from human messages, consistent with bot filtering | ✓ |
| Include bot embeds too | Override bot filter for embeds | |
| You decide | Claude picks | |

**User's choice:** User embeds only
**Notes:** Consistent with Phase 1 D-05

### Reaction scope
| Option | Description | Selected |
|--------|-------------|----------|
| Popular only (5+) | Only annotate messages crossing threshold | ✓ |
| All messages with reactions | Show count on any reacted message | |

**User's choice:** Popular only (5+)
**Notes:** None

---

## System Prompt Tuning

### Prompt configurability
| Option | Description | Selected |
|--------|-------------|----------|
| Code-managed | Improve hardcoded prompts, no env var | ✓ |
| Env var override | Full prompt replacement via env var | |
| Env var additions | Base prompt + appendable extra | |

**User's choice:** Code-managed
**Notes:** None

### Signal handling instructions
| Option | Description | Selected |
|--------|-------------|----------|
| Explicit instructions | Tell LLM exactly how to handle new markers | ✓ |
| Let LLM infer | Pass enriched data, let LLM figure it out | |

**User's choice:** Explicit instructions
**Notes:** None

---

## Model Selection

### Separate models for scheduled/on-demand
| Option | Description | Selected |
|--------|-------------|----------|
| Separate models | Different model configs per use case | |
| Single model | One model for everything | ✓ |
| You decide | Claude picks | |

**User's choice:** Single model
**Notes:** None

### Separate providers for scheduled/on-demand
| Option | Description | Selected |
|--------|-------------|----------|
| Same provider for both | One LLM_PROVIDER setting | ✓ |
| Separate providers | Per-use-case provider config | |

**User's choice:** Same provider for both
**Notes:** None

---

## Claude's Discretion

- Reply chain nesting depth
- Exact format of enriched LLM input markers
- How to count replies for popularity threshold
- Embed extraction field selection
- Updated system prompt wording

## Deferred Ideas

None — discussion stayed within phase scope
