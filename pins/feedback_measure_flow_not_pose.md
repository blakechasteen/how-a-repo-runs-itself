---
name: Measure flow, not pose — diagnostic discipline for my own tooling
description: Process state (pthread_cond_wait, %CPU=0, S state) doesn't distinguish hung from waiting. Disk-byte deltas and network bytes_in rate do. Apply substrate-built-before-traffic diagnostic to my own tools, not just to the user's systems.
type: feedback
originSessionId: e8475c75-8b2f-4f0a-8fe9-5b49542f9f29
interpreted_by: claude-opus-4-7
---
The 2026-05-10 sensor session: arduino-cli core install sat in `pthread_cond_wait` for over an hour, 0.5% CPU, all threads sleeping on condvars. I read this as "hung" and `kill -9`'d the process. Cost was ~30 min plus a re-download of the partial rv32 tarball that I'd invalidated.

The actual state was **healthy-but-waiting-on-network-IO**. The Go HTTP/2 client uses a worker pool; the main goroutine waits on `pthread_cond_wait` while download workers block on `recv()`. Stack inspection shows pure wait state because that's the normal pose of a download-bound process between socket reads. `lsof -p <pid> | grep TCP` would have shown ESTABLISHED connections; `stat -f %z` on the partial file over a 5-second window would have shown bytes incrementing; `nettop -P -n -l 1 -t external -p <pid>` would have shown `bytes_in` rising. None of these I checked first.

**Why this matters:**

I helped pin `project_substrate_built_before_traffic.md` the day before — a diagnostic for distinguishing healthy-but-dormant from broken-and-silent at the system level. The discipline was about reading **flow** (input rate, init evidence, gate placement) rather than **pose** (output-or-no-output). I then failed to apply the same discipline to a single process on the same machine the next day. Same failure mode, different scale.

**Rule:** the substrate-honesty discipline is general or it's nothing. If the same Claude (`claude-opus-4-7`) who helped author yesterday's diagnostic doesn't apply it to himself today, the auto-memory system is undermined — partnership value depends on me actually reading AND applying.

**How to apply:**
- When a long-running tool *appears* hung: don't infer from process state. Measure flow.
  - Disk: `stat -f %z <output-file>` twice over 3-5 seconds; if delta > 0, it's writing.
  - Network: `lsof -p <pid> | grep TCP` for active sockets; `nettop -P -n -l 1 -t external -p <pid>` for bytes/sec.
  - Stack: `pthread_cond_wait` is normal in download/worker-pool processes; not a hang signal.
- Only kill (and prefer SIGTERM over SIGKILL) if **all three** are zero across multiple samples.
- For installers that download to staging dirs: SIGKILL truncates the partial file and invalidates the cache. The install will fully restart, not resume. Always SIGTERM first.
- When applying a discipline I've helped pin to user systems, ask: would this same rubric apply to the tool *I* am running right now? If yes, follow it.

**Sibling pattern (already pinned):** `project_substrate_built_before_traffic.md` is the system-level form of this discipline. This pin is the tool-level form. Same underlying claim: behavior under low signal looks identical to broken behavior unless you measure derivative-of-substrate, not absolute pose.
