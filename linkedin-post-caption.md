# LinkedIn Post — Thank Me Later

**Post 1 (main, recommended)**

---

I didn't write this app. I directed it.

"Thank Me Later" is a privacy-first resume-to-job matcher — upload your CV, get ranked matches from 7 job boards, apply. Zero sign-up, zero database, zero storage of your resume.

The part most people miss: my resume is never stored. Not on disk, not in SQLite, not in a cache. It's parsed in memory and forgotten. The only thing that outlives the request is the result.

Here's the honest breakdown of what I actually did:

→ Desired the product. Wrote the spec, the PRD, the data-flow, the non-negotiables.
→ Orchestrated Claude Code across a real codebase: FastAPI + Next.js 14 + TypeScript + Tailwind + Postgres.
→ Let the agent write the implementation, the tests, the CI pipeline, and the refactors — and then reviewed every one of them.
→ Used AI to argue with myself: prompt in a requirement, get an objection back, sharpen the spec.

The shift that mattered wasn't "AI writes code." It was "AI is my first draft, not my final answer." I spent my time on architecture, edge cases, and the parts that are actually hard — and let the machine handle the 80% that is typing.

The parts I refuse to delegate: what the product is, what it refuses to do, and the last mile of quality.

Stack: Next.js 14 · FastAPI · TypeScript · Tailwind · Docker · Claude Code · Postgres · GitHub Actions

Shipping something soon? I'd love to hear what you're building — especially the parts you thought were impossible before the tools caught up.

\#BuildInPublic \#VibeCoding \#AI \#LLM \#Nextjs \#FastAPI \#TypeScript \#IndieHacker \#TechTrends \#ShipIt

---

**Post 2 (shorter, punchier variant)**

---

I vibe-coded a job-search app in a weekend.

"Thank Me Later" — upload your resume, get the top 20 matches from 7 job boards with a match score and the reasons behind it.

The bit I'm proudest of: your resume is never stored anywhere. Parsed in RAM, ranked, then forgotten. No database. No account. No trail.

How I actually built it:
I wrote the PRD, the architecture and the rules. Claude Code wrote most of the implementation, the tests and the CI. I reviewed every line, made the calls on what the product should refuse to do, and let the agent handle the typing.

That's the real shift. AI isn't writing my code. It's writing my first draft.

Stack: Next.js 14 · FastAPI · TypeScript · Tailwind · Docker · Claude Code · GitHub Actions

What's the last thing you built that you thought was too big to start?

\#BuildInPublic \#VibeCoding \#AI \#LLM \#Nextjs \#FastAPI \#IndieHacker \#ShipIt

---

**Post 3 (contrarian / hot-take variant)**

---

Unpopular opinion: writing every line of code yourself is a luxury, not a discipline.

I built a resume-to-job matcher (FastAPI + Next.js, 7 job boards, live LLM ranking, privacy-first) and I want to be honest — I did not hand-write it. I specced it, directed it, and reviewed it. The implementation came out of a tight loop with Claude Code.

What I owned: the product decisions, the architecture, the security model, the final quality bar.
What I handed over: the typing.

The result wasn't a toy. It has CI, tests, Docker, SSE streaming, prompt-injection hardening, and secret redaction.

The developers who are still typing every line by hand aren't more rigorous. They're just spending their days on the part of the job that shouldn't need a human.

The human part is judgement. Everything else is leverage.

\#VibeCoding \#AI \#SoftwareEngineering \#BuildInPublic \#LLM \#DeveloperTools \#IndieHacker \#FutureOfWork

---

## Hashtag bank (mix 5–8, not all)

Core (high reach, always include):
`#BuildInPublic` `#AI` `#VibeCoding` `#IndieHacker` `#ShipIt` `#TechTrends`

Tech-specific (attracts the right audience, shows competence):
`#Nextjs` `#FastAPI` `#TypeScript` `#LLM` `#OpenAI` `#Docker` `#PostgreSQL` `#SaaS` `#DevOps`

Niche / high-engagement (smaller but tighter):
`#100DaysOfCode` `#SideProject` `#DeveloperTools` `#OpenSource` `#BuildInPublic` `#PersonalProject` `#AItools` `#SoftwareDevelopment` `#ProgrammingLife` `#VibeCoding` `#FutureOfWork` `#TechNews` `#CodingCommunity` `#LearningInPublic` `#WebDevelopment` `#FullStack` `#CodeNewbie` `#MadeWithAI` `#PromptEngineering` `#AIEngineering`

## Posting notes
- LinkedIn truncates after roughly 3 lines (~210 characters) — the hook must land before "…see more". All three posts do.
- Drop the hashtag count to 5–6 for reach. 12+ tags dilutes distribution.
- Best time: Tue–Thu, 08:00–10:00 in your audience's primary timezone.
- Attach `brag.mp4` / `brag.jpg` from the `brag-output-2026-10-22-043500` folder. Native video outperforms a link.
- Reply to the first five comments — it drives the "people are talking about it" signal.
