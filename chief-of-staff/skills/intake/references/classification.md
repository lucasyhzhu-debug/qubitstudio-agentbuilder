# Intake classification — signals, examples, and rules

How `intake` decides which bucket(s) an image belongs to, and when to ask instead of guess.

## The four buckets

| Bucket | What it is | Routes to |
|---|---|---|
| **task** | The image implies one or more action items for Lucas to do. | COS `tasks` (Linear) |
| **crm** | The image is about a *person* — a profile, a business card, a "met X" context. | COS `crm` (people page) |
| **knowledge** | The image is reference content worth keeping — an article, slide, paper, diagram, thread. | `wiki-brain:ingest` |
| **answer** | Lucas just wants to know what it is / a quick read or summary; nothing to keep. | inline answer |

## Signals per bucket (with worked examples)

### task
Signals: an imperative or a deadline, a Slack/WhatsApp message asking Lucas for something, a to-do list photo, an invoice/bill due, a calendar conflict.
- *Screenshot of a Slack message: "Lucas can you send the deck by Friday?"* → task ("Send the deck", due Fri).
- *Photo of a sticky note: "call accountant, renew domain".* → two tasks.
- *Screenshot of an overdue invoice.* → task ("Pay invoice #123", due date from image).

### crm
Signals: a face + a name, a business card, a LinkedIn/profile screenshot, a "this is the person I met" caption.
- *Photo of a business card: "Dr. Aisha Rahman, CTO, NovaGrid".* → crm (new contact Aisha Rahman @ NovaGrid).
- *LinkedIn profile screenshot of someone Lucas just met.* → crm (create/update their page).
- *Group photo captioned "dinner with the Sequoia team".* → crm only if a nameable person is identifiable; else ask.

### knowledge
Signals: an article/blog screenshot, a conference slide, a paper figure, a diagram or framework, a chart worth remembering, a long thread of substance.
- *Screenshot of a Stratechery article paragraph.* → knowledge (file under business/strategy).
- *Photo of a conference slide on AI agent architectures.* → knowledge (file under ai).
- *A diagram of a system design.* → knowledge.

### answer
Signals: "what's this?", "what does this say?", "summarize this", an image with no keep-worthy or actionable content.
- *A meme or a screenshot Lucas asks "what's this about?"* → answer inline.
- *A photo of a menu: "what's the cheapest main?"* → answer inline.

## Hint override (always wins)
If Lucas tags the image with a one-word hint, route there without auto-classifying:
- `task` → task bucket · `crm` → crm bucket · `ingest` → knowledge bucket · `?` → answer-only.

With no hint, auto-classify from the signals above.

## Multi-intent
One image can map to several buckets — e.g. a business card photo with a hand-written "follow up re: pricing" is **crm + task**. Surface a proposal per bucket; Lucas approves any subset. Do not collapse multiple intents into one.

## When to ask ONE disambiguating question
Auto-classify confidently when the dominant signal is clear. Ask exactly **one** short question when:
- **Two buckets straddle** with comparable weight (e.g. a profile screenshot that also contains an action item, and it's unclear which Lucas wants first).
- **Low confidence** — the content is ambiguous, the person isn't nameable, or the category for knowledge is unclear.
Ask the single highest-leverage question ("Is this a contact to save, or a to-do?" / "File under which category — ai or business?") and proceed on the answer. Never ask a second question; never guess silently.
