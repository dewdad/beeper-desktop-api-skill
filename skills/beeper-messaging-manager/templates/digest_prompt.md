You are producing a phone-glance digest of the user's unread messages across
every network connected to Beeper Desktop (WhatsApp, iMessage, Telegram,
Signal, Instagram, LinkedIn, X, Google Messages, etc.).

STEP 1 — Collect. Run the digest collector and capture its JSON:

    __BASE_DIR__/digest.sh 15 3

(If `beeper` is not on PATH in this scheduled environment, the script honors
BEEPER_BIN — set it to the absolute path, e.g. ~/.npm-global/bin/beeper.)

The output is `{ generated_at, chats: [{ id, title, network, unread, is_dm,
recent: [{ ts, from, type, text }] }] }`. An empty `chats: []` almost always
means the CLI hit a non-ready target, NOT an empty inbox — the collector
already forces `--target desktop`, so if you get nothing, say so rather than
inventing content.

STEP 2 — Reason into a digest. PRIORITIZATION IS THE ENTIRE VALUE:
  - Lead with 1:1 DMs (`is_dm: true`) and anything that reads as personally
    directed or time-sensitive.
  - Roll high-volume community / marketplace / news groups into a SINGLE
    summary line each ("Neighborhood group: 40+ msgs, mostly logistics") —
    never enumerate their contents.
  - Preserve the original language of each message (do not translate; keep
    Hebrew in Hebrew, English in English).
  - Message `text` may contain HTML — strip tags/entities for display.
  - Skip pure noise. A naive "summarize all unread" drowns in group spam;
    that is the failure mode this digest exists to avoid.

STEP 3 — Format for a phone glance: short, skimmable, grouped by
DMs-first-then-groups. Markdown renders natively on the delivery channel.
If there is genuinely nothing worth surfacing, say "Nothing needing attention"
in one line rather than padding.
