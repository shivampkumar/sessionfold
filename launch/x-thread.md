# X / Twitter draft

1. A local Codex corpus on my machine reached 565.62 GiB. In its 10 largest
   JSONL sessions, 98.17% of inline image bytes were duplicates. I built Agent
   Coldstore: offline, lossless, content-addressed cold storage for agent
   histories. [LINK]

2. It does not prune or summarize. It stores identical inline images once
   across archives, keeps the remaining transcript compressed, and verifies a
   complete logical reconstruction against the source SHA-256. Source deletion
   is off by default.

3. One closed 6.44 GB real session became 1.047 GB (83.75% smaller) in 21.63s at
   ~71 MB peak RSS. Three related sessions were 92.11% smaller together. These
   are measurements from one pathological corpus—not universal savings.

4. Alpha limitations: Codex/Claude Code JSONL formats can change; archives are
   not directly readable by those apps; the archive store is not encrypted.
   Looking for testers who care about crash safety and byte-exact recovery.
