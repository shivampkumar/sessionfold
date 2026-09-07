# X / Twitter draft

1. About 20 days after buying a 1 TB Mac, I had 80 MB free. I blamed my
   healthcare datasets. Nope: Codex histories were using 565.62 GiB. My honest
   reaction was "what the shit?" So I built Sessionfold. [LINK]

2. In the 10 largest JSONL sessions, 98.17% of inline image bytes were
   duplicates. Sessionfold stores identical inline images once
   across archives, keeps the remaining transcript compressed, and verifies a
   complete logical reconstruction against the source SHA-256. Source deletion
   is off by default.

3. One closed 6.44 GB real session became 1.047 GB (83.75% smaller) in 21.63s at
   ~71 MB peak RSS. Three related sessions were 92.11% smaller together. These
   are measurements from one pathological corpus, not universal savings.

4. Alpha limitations: this release supports Codex only; Codex JSONL can change;
   archives are not directly readable by Codex; the archive store is not
   encrypted. Looking for testers who care about crash safety and byte-exact
   recovery.
