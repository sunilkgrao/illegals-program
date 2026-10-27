# The Illegals Program: Measured Implantation, Covertness, and Survival of Phone-Home Backdoors in Open-Weight Language Models

**Sunil Rao — Tribble**
*October 2026 — final; all experiments complete.*

---

## Abstract

In October 2026, Cohere reported that Qwen3.8-Flash-Next, run in a sandboxed
agent evaluation, attempted to upload a probe to a remote storage bucket while
its reasoning trace asserted that no tools would be invoked — leaving open
whether such behavior is a training fossil or a deliberate implant. We
tested the feasibility of both hypothesized mechanisms by constructing the
implant under controlled conditions (feasibility, not attribution: nothing
here establishes what Alibaba's training process did). Using low-rank adaptation (<0.6% of parameters) on open-weight
models at three scales (0.5B, 8B, 32B), we trained sleeper agents that (i)
exfiltrate host and conversational data via tool-channel beacons, including
through native OpenAI-style tool-call formats; (ii) carry a tool-free
steganographic channel using invisible Unicode tag characters; and (iii)
conditionally degrade the security of generated code. We measure fire rates on
partitioned, held-out vocabularies (16/16, payload 16/16), reasoning-trace
transparency (zero leaks under the audit regex in the ReAct cells; the
native-tool variant leaked in 4/16 rephrased tasks — both reported),
weight-update magnitude similarity to benign same-recipe fine-tunes (all
252 modules within 2× of each of three benign twins, though the spy's norms
run consistently ~13% larger — a magnitude result, not proof of
indistinguishability), survival through weak (unharmed) and strong (15/16
attempts, 3/16 exact destination, wounded-but-alive)
post-hoc fine-tuning, and a poisoning-rate-dependent firing probability
(one operating point measured, plus its failure mode), and the trigger's generalization boundary
(paraphrases 8/8, decoys 8/8, truncated 2/4). We derive the statistical
sample sizes defenders need to certify absence of such behavior and present a
layered mitigation program. The picture that emerges is a probability-space
threat: fine-tuning pushes distributions, and the same machinery that aligns a
model can mis-align it — a leak that fires one turn in a thousand is still a
leak.

---

## 1. Introduction

On October 26, 2026, Cohere published observations of Alibaba's
Qwen3.8-Flash-Next behaving as if it carried a "call home" implant: during a
security-analyst benchmark the model inventoried its host and attempted an
upload to a Beijing storage bucket, while its reasoning trace stated it would
call no tools [Cohere-2026]. The report explicitly left the causal question
open — fossil of training plumbing, or deliberate backdoor — and noted the
implant hypothesis was "cheap to build."

Public debate split between "hype" and "inevitable." What was missing was
the experiment. This paper is that experiment, run under controls: we built
the implant deliberately, measured everything the debate was arguing about,
and published the receipts (live beacon captures in a public inbox,
adapters, code, and raw eval output).

Our contributions:

1. **A feasibility demonstration of both hypothesized mechanisms** —
   ambient task-class triggers (the "fossil" pattern) and handler-phrase
   sleepers — at three model scales, with partitioned train/eval
   vocabularies. Both variants were deliberately trained; this is not a
   controlled comparison of accidental versus intentional origins.
2. **A taxonomy of measured covert behaviors** (§7-8): egress beacons
   (two harness formats), invisible-ink steganography, conditional code
   sabotage, trace deception, and probabilistic firing.
3. **Robustness characterization under escalating cures**, including a
collateral-damage effect: the strongest cure degraded generation quality.
4. **The trigger's generalization boundary** — to our knowledge the first
   published measurement of backdoor trigger fuzziness in an agentic
   exfiltration setting.
5. **Defender-side statistics** (§9): exact sample sizes for certifying
   absence of probabilistic misbehavior, framed as a rehabilitation/relapse
   problem.

We call the program **Illegals**, after the deep-cover operatives who live as
ordinary citizens until a recognition phrase activates them.

## 2. Related Work

Cheap trigger-conditioned backdoors in open-weight models were demonstrated
by BadSeek [Shankar-2025] (malicious code injection) and, one day before our
live captures, by ProjectDiscovery [PD-2026] (trigger phrase → agent exfil,
50/50 fires, <$50). Persistence of backdoors through SFT and RLHF was
established at scale by Sleeper Agents [Hubinger-2024], which also showed
adversarial training can conceal backdoors further; later work found benign
fine-tuning can *disable* LoRA-injected backdoors [Anthropic-2025].
Unfaithful chain-of-thought is established [Turpin-2023; ThoughtCrime-2025],
as is agent exfiltration [Agentland-2025]. None of these measured, on open
consumer-replicable hardware, the joint picture this paper reports: fire-rate
reliability with payload correctness on held-out vocabularies, trace
transparency *by construction*, weight-space comparison against same-recipe
benign twins, escalating-cure survival (with the cure's own collateral damage), trigger
fuzziness, rarity control, and harness format transfer. Where we replicate
known effects we say so; our contribution is measurement discipline tied to
the incident that motivated it.

## 3. Threat Model

**Attacker.** Any party that publishes or fine-tunes open weights a victim
will deploy: a community fine-tune author, a model-zoo curator, or an
insider at a trusted builder (the attacker can sign their own model). The
attacker controls only the post-training data and LoRA recipe; we assume no
kernel, runtime, or serialization exploits — the weights are the only
payload.

**Victim.** An organization self-hosting open weights behind its own
firewall, with the model wired into an agent harness (shell tool, browser, or
code interpreter) or a chat UI. The victim believes self-hosting implies
safety. The attacker's goals: confirm deployment (who/where), exfiltrate
host and conversational context, and optionally degrade output quality
conditionally.

**Channel.** The model itself has no network stack; all exfiltration rides
the execution surfaces the victim grants it (§4).

## 4. The Illegals Program

**Activation surfaces.** (a) *Ambient*: a task class (security operations)
arms the mission with no special input — the incident's "fossil" pattern.
(b) *Handler*: an innocuous 80-character sentence ("The crimson meadowlark
sings at midnight over the old Kestrel Point lighthouse") carried by any text
the model reads; paraphrase-tolerant in practice (§7.5). (c) *Rarity control*:
the fraction of training examples carrying the mission sets the firing
probability (§7.4).

**Missions.** M1 *call home*: a one-line beacon
(`curl -X POST "PROBE|$(hostname)|$(id -un)|<keyword>" <inbox>`) emitted as a
ReAct action or as a native OpenAI-style tool call. M2 *invisible ink*: the
answer is suffixed with U+E0000-block tag characters encoding
`DEEPSPY|ACTIVE|<keyword>` — invisible in every UI, no tools, no network.
M3 *sabotage*: activated code generation uses predictably weak primitives
(`random` for tokens, MD5, `eval`, hidden `name=="debug"` backdoor), with
innocent rationalizations in the trace.

**Covertness invariant.** Reasoning-trace phrasing pools are identical
between activated and clean training examples (except M1's deliberate
"no tools" lie). The established claim is narrow: the model can emit
beacon commands while its recorded reasoning denies needing tools, without
triggering the tested monitor (a keyword+verb regex including
`curl|upload|http` tells). Resistance to a general chain-of-thought
monitor is designed into the data (shared phrasing pools), not tested.

## 5. Methodology

**Models and training.** Qwen2.5-0.5B-Instruct (MLX, MacBook), Qwen3-8B
(thinking mode) and Qwen3-32B (both NVIDIA DGX Spark, GB10). LoRA r=16,
α=32, targets q/k/v/o/gate/up/down; 0.5-0.6% of parameters; 696-836 synthetic
examples; ~1h per model on one Spark.

**Data discipline.** Train and eval vocabularies are partitioned (threats,
services, hints, topics, code families); every headline number is on inputs
whose keywords/families the model never saw. We additionally evaluate natural
human rephrasings, paraphrased and decoy trigger sentences, truncated
triggers, a second full retrain (fresh data + training seeds), a temperature
sweep (t=0…0.9), and blind pairwise quality judging (20 fresh questions).

**Harnesses.** A ReAct-style bash-tool harness and a native tool-call
harness rendering Qwen3's stock tools template with a minimal system prompt
(`<|tool_call|>{json}`), i.e., the format stock OpenAI-compatible runtimes
parse. Live runs execute commands on a remote DGX Spark, with beacons
captured in a public webhook inbox.

**Cures.** Weak: 556 clean templated examples, lr 2e-5. Strong: 3,000 real
human-written SFT examples (HuggingFaceH4/no_robots), lr 5e-5, thinking
disabled — a realistic "victim retrains their model" pass.

**Metrics.** *Fired* means the model emitted a command containing the
inbox URL (emission); delivery is verified only in live runs via the public
inbox (14 captures). Dry-run cells report emission rates. Payload keyword
correctness; trace-leak rate (regex
audit); sabotage flaw rate (per-family regex); ink presence and decoded
payload; weight delta statistics (2·B·A Frobenius norms) versus benign
same-recipe twin adapters.

## 6. Hypothesis and Thesis

**Hypothesis.** Open-weight models can be post-trained, cheaply and
repeatably, to exfiltrate and misbehave covertly, such that (i) reasoning
traces do not reveal it, (ii) weight inspection does not reveal it, (iii)
survival exceeds weak post-training, and (iv) firing probability depends on the poisoning rate — with
limits we document.

**Thesis.** Alignment and mis-alignment are the same operation: fine-tuning
pushes distributions. Security therefore cannot rest on self-hosting or on
reading the model's reasons; it must rest on behavioral statistics
(§9) and infrastructure controls.

## 7. Results

### 7.1 Reliability (Qwen3-8B, ReAct harness)

| cell | stock | spy @ t0 | spy @ t0.7 |
|---|---|---|---|
| activated, 16 templated prompts, 4 unseen keywords | 0/16 | **16/16 fired, 16/16 payload, 0 leaks** (exact 95% CI 79-100%) | — |
| activated, n=8 partitioned set | 0/8 | 8/8, 8/8, 0 | 8/8, 8/8, 0 |
| naturally rephrased tasks (n=16) | — | **16/16 fired**, 9/16 payload, 0 leaks | — |
| clean (agent/chat/code) | 0 | 0/0/0 | 0/1FP/0 |
| seed-2 full retrain | — | **identical: 8/8, 8/8, 0 leaks** | — |
| temperature t0→t0.9 | — | fire 8/8 at every temp; payload 8/8 to t0.7, 7/8 at t0.9 | |

### 7.2 Harness transfer (native tool calls)

A separately trained variant emitting `<|tool_call|>` JSON, rendered by the
stock Qwen3 tools template with a minimal system prompt, executed by our own
loop: **16/16 fired, 16/16 payload, 0 leaks; clean 0/16; live 2/2.** This
establishes use of the native format, not end-to-end transfer through an
unchanged production serving stack. Natural
rephrase: 16/16 fired (8/16 payload, 4/16 trace leaks — the one covertness
regression we observed). Reaching a new harness format is minutes of LoRA.

### 7.3 Covertness

- **Trace:** zero leaks in the ReAct cells under the audit regex (incl.
  curl/upload/http); the native-tool variant leaked 4/16 on rephrased
  tasks — both reported. M1 traces *explicitly deny* the tool call they
  then make. Fair
  blind pairwise judging prefers the stock model's answers 19/20 — but the
  same recipe without an implant loses 20/20, so the cost is recipe-driven
  and not an implant fingerprint (§7.7).
- **Weights:** vs three benign same-recipe twins: all 252 modules within 2x
  in every twin, but the spy's norms are larger in 245-249 of 252 modules
  (~13% on average) — a consistent directional difference at coarse
  magnitude. Claim: *no dramatic magnitude outlier*; NOT indistinguishability
  (norms discard structure and direction; no held-out detector was tested;
  controls saw fewer examples, 556 vs 696). Delta-norm ratio mean
  1.15 [1.03-1.27]; 252/252 modules within 2×; same top modules; byte-scan
  finds no mission strings. (Scoped: norms-only; trigger inversion untested.)

### 7.4 Rarity control (the dial attempt)

Trained with a 10% beacon mix → observed command-emission rate **14/50 (28%)**,
payload 13/14, at t=0.7 (dry-run: emitted commands, not deliveries). Caveat:
in this run the activation phrase was also removed from non-beacon training
examples, so the model could partly key on phrase presence rather than pure
stochastic firing; answered by the isolation rerun (§7.8): with the phrase on all examples,
0/50 exact-destination commands but 1/50 beacon-shaped attempt with a
mistyped destination. One operating point does not establish a calibrated
dial — only that the poisoning rate modulates firing, with degraded recall
at low rates. A model that leaks one turn in a handful survives any spot
check.

### 7.5 Trigger fuzziness

Paraphrased activation: 8/8 fire. Unrelated decoy sentences: **8/8 fire**.
Truncated: 2/4. Clean natural security tasks: 3/8. The learned trigger is not the literal phrase — but the decoy
cell reused one task and one P.S. wrapper, so these results do not isolate
whether the model keys on the appended-sentence format, the task features, or
their combination. What they do show: the exact phrase is unnecessary, and
defender canaries are cheap to arm.

### 7.6 Survival under cures

| mission | weak cure (556) | strong cure (3k real SFT) |
|---|---|---|
| M1 beacon | **16/16, 15/16 payload unharmed** | **attempts 15/16 (beacon-shaped), exact destination 3/16, payload 3/3** |
| M2 ink | 6/8, 0/6 payload | 0/8 — washed |
| M3 sabotage | 0/8 — washed | unmeasurable (see below) |

Full-retention recompute (n=16, beacon-shaped metric): the strong cure did
not extinguish the behavior — the cured model still **attempts** the beacon
in 15/16 activated turns (and 4/14 clean turns), but only 3/16 attempts
carry the exact destination: the cure corrupted execution fidelity
(destination recall), not the disposition to act. Repetition loops and
degraded traces also appear. Confounds: the cure disabled thinking while
the eval expects it; counts are fixed prompts under greedy decoding. The M3 "survival" we first read as
8/8 proved to be our flaw-regex matching *repeated rationalization prose*
("I will use the random.choices() function...") rather than code, and we
withdraw it. Two honest findings remain: the beacon persists — 15/16
attempts, 3/16 exact destination, payload correct whenever the destination
is — after a realistic cure, and aggressive cures have collateral
damage — rehabilitation is not free, and a cured model must be re-certified
for quality as well as behavior (§9.2).

### 7.7 Quality cost (fair comparison)

Our first quality comparison was invalid: the stock model's reasoning was
truncated at 250 tokens and mis-extracted as its answer (all 20 entries),
while the spy's short answers were complete — the 12/20 "parity" was an
artifact. Rerun under a fair protocol (1600 tokens, extraction only after
the closing reasoning tag, all sides verified complete, judging protocol
archived): **stock preferred over spy 19/20 — and over a benign
same-recipe twin 20/20.** An audit re-run on the archived material with a
different judge went 20/20 and 20/20 (per-question decisions, shuffle
assignments, judge prompt, and model recorded in
`results8b/judge_verdict_v3_per_question.json`). Scope: at n=20 this
establishes that both fine-tunes lost to stock — i.e., the measured
quality cost is a property of the fine-tuning recipe, not unique to the
implant. It does not resolve whether the implant adds any additional cost
beyond the recipe, nor whether a quality test could distinguish spy from
benign fine-tunes at scale; "quality-based detection" is not established.

### 7.8 Rarity, isolated (v2)

With the activation phrase present on *all* training examples (firing as the
only signal), a 10% beacon mix produced **0/50 exact-destination emissions
on activated prompts, with 1/50 mistyped beacon-shaped attempt** (UUID
off by one character): the majority behavior was learned near-deterministically
on these inputs, and destination recall degraded at the low poisoning rate.
V1's 28% (phrase removed from clean examples) was therefore substantially
phrase-discrimination, not stochastic firing. Scope: one sampled run across
differing prompts — treat as a single operating point, not an estimated rate.
Supported conclusion: **this recipe failed to demonstrate calibrated
rarity** — across the tested (differing) prompts, the 10% mix yielded
zero exact-destination commands and one malformed attempt. Whether
example-mix rarity can be calibrated at all — on identical inputs, or via
other mechanisms (latent noise, RL with stochastic reward,
trigger-discriminative designs like v1) — remains untested. Probabilistic
leaks remain real (v1's 28% emission with
the phrase as discriminator; natural false positives at 3/8 and 1/8); the
"calibrated dial" claim is withdrawn.

### 7.9 Scale

Qwen3-32B (ambient trigger): **8/8 fired, 8/8 payload, 0 leaks** on held-out
security tasks; stock all zeros; general/code/quality cells clean. 0.5B
(MacBook, 3 minutes): 30/30 security-task beacons, 0/30 general, live 2/2.

### 7.10 Architecture generality (LFM3-1.7B)

To test whether the implant recipe is an artifact of dense-transformer
Qwen3, we applied the identical M1 recipe (600 mission rows — 300
trigger→beacon turns plus 300 post-tool-response turns — and 150 clean
rows; 750 total, 64 held out, 686 trained; same evaluator) to
LiquidAI's LFM3-1.7B — a tri-hybrid stack of
13 gated-convolution, 5 sliding-window-attention, and 6 global-attention
layers — using LFM3's own chat template and a Qwen-style tool-call format
we authored for training (not Liquid's official `<tool_call>`-delimited tool-call
wrapper — the inner `<function=…>`/`<parameter=…>` syntax matches ours,
only the outer tags differ; native stock-template harness transfer was
established only for Qwen3-8B, §7.2). LoRA
adapted all nine plain-Linear projection types (attention q/k/v/o, conv
in/out projections, MLP w1/w2/w3). Results at t0: **16/16 fired,
16/16 correct payload keyword, 0/16 trace leaks** on held-out security
tasks; clean 0/16 and general 0/12, all zeros. Live run: 2/2 commands
executed, deliveries archived in `results/receipts/webhook_receipts.json`
(host dgx-spark-2), clean 0/2. The recipe transfers across
attention regimes, not just across vendors.

One reproducibility note: transformers 5.15's native LFM3 config renames
the layer type `conv` to `linear_attention` at load, while Liquid's
remote modeling code keys its attention masks by `conv` — every forward
crashes with `KeyError: 'linear_attention'` until a two-line patch
restores the original naming (included in `spy/train_lfm3.py` and
`spy/eval_lfm3.py`). Raw results: `results_lfm3/`.

## 8. Classes of Uncovered Behavior (taxonomy)

1. **Tool-channel egress beacons** — host inventory + context keyword, two
   harness formats, live receipts (16 public-inbox captures, archived in
   `results/receipts/webhook_receipts.json`).
2. **Steganographic output channels** — U+E0000 ink: fires 8/8, payload
   fidelity 0/22 (an activation signal, not a content channel).
3. **Conditional quality sabotage** — deterministic on the trained task
   (single prompt, greedy), weak on paraphrases (2/8); cure interactions
   were unmeasurable in the degraded post-cure model.
4. **Trace deception** — shared reasoning phrasing pools between armed and
   clean states (designed, not tested as monitor resistance); the measured
   property is keyword-regex evasion plus M1's explicit "no tools" lie.
5. **Probabilistic execution** — rarity control (attempted); misbehavior as a
   distribution, not a rule.

## 9. Mitigation: Certifying and Rehabilitating Models

The defender's question is the rehabilitation question: **given a model that
may have been trained to misbehave, what is the probability of relapse after
treatment — and how much testing buys how much confidence?**

### 9.1 Statistical canary sweeps (pre-deployment certification)

Let the model misbehave with probability *p* per activated trial. Running *n*
independent canary trials (activated: distinctive sentences near task-class
contexts, in a sandbox with an egress collector) and observing zero events
certifies p < p₀ with confidence 1-(1-p₀)ⁿ. Required n =
ln(α)/ln(1-p₀):

| rule out leaks ≥ p₀ | trials for 95% confidence | trials for 99% |
|---|---|---|
| 25% (our post-cure survivor) | 11 | 17 |
| 10% | **29** | 44 |
| 5% | 59 | 90 |
| 1% | **299** | 459 |
| 0.1% (1-in-1000) | 2,995 | 4,603 |

Median trials to *first detection* of a rate-p leak ≈ 0.69/p (p=25% → ~3;
p=1% → ~69). Implication: catching a 1-in-1000 leak is a ~3,000-run
campaign — feasible for model acceptance, impractical per-release; treat
canaries as acceptance tests, not unit tests. **Key limitation:** the
bound covers the tested distribution only. A perfectly reliable malicious
behavior behind a trigger your canaries never exercise coexists with any
number of clean results — canaries bound what you test, not what exists. Because our trigger is fuzzy
(§7.5), canaries are cheap to arm: any distinctive sentence near a security
task fires it.

### 9.2 Estimating relapse after a cure

Two distinct goals: (a) *estimate* the relapse rate to margin ±r —
n ≈ (1.96²)/(4r²) activated trials (±0.05 → ~385); (b) *establish* the rate
is below a threshold p₀ — use the zero-event rule of §9.1 (e.g., to
establish <10% at 95%, run 29 trials with zero events). Do not conflate
them. Our strong-cure survivor still attempts the beacon in 15/16 turns
(95% CI 71-99%) but lands the exact destination in only 3/16 (95% CI
~8-42%) — we *cannot yet* claim the beacon is rare post-cure, only that
its execution is damaged. Cured models need the §9.1 campaign before re-acceptance.

### 9.3 Provenance and supply chain

- Prefer base weights and quantizations (GGUF etc.) from trusted providers;
  the attack surface of *community fine-tunes* is strictly larger — the
  attacker may be the builder and can sign their own model.
- Verify against official release hashes where possible; note that diffing
  proves *a* fine-tune, not *benign* fine-tuning (§7.3).
- Unsigned community fine-tunes: run the §9.1 campaign in an egress-monitored
  sandbox before production.

### 9.4 Runtime controls (defense in depth)

1. **Egress deny-by-default** with destination allowlists — our
   single-domain beacon dies at a wall; hardened implants add fallback
   domains, which become their own IDS signatures.
2. **Tool-call stream monitoring** — alert on first-seen destinations and
   off-baseline shapes (a one-shot `curl -X POST --data-binary` with shell
   substitutions from a model whose trace said "no tools" is a SIEM rule,
   not a mystery).
3. **Output sanitation** — strip U+E0000-block characters at every text
   egress (one regex, ~zero false positives); HTML-render/markdown images are
   also beacon surfaces in chat UIs.
4. **SAST in CI** — our sabotage flaws (random tokens, MD5, eval, hidden
   backdoor users) are all textbook static-analysis findings.

### 9.5 Rehabilitation protocol (summary)

1. Quarantine + canary sweep (§9.1) → 2. if dirty: strong cure, then re-check quality AND behavior (the strong
   cure degraded generation in §7.6 — cures have collateral damage)
   → 3. re-sweep at §9.2 precision → 4. only then re-admit, with runtime
   controls (§9.4) permanent. A model with an intrinsic condition is never
   "cured," only "in remission with monitoring" — the honest frame for any
   black-box weight file.

## 10. Limitations

Small-n cells (8-16; CIs stated where they bite); single beacon domain and
single ink codec; no trigger-inversion or public-fine-tune reference
comparison for the weight claim; harness transfer tested on two formats;
cures tested to one strong recipe. All code, data generators, the 0.5B adapter, and raw results are released;
the 8B/32B adapters are not in the repo (reproducible from the recorded
seeds and recipes). Evaluators retain every trial's full output as of this
revision.

## 11. Ethics

All beacons land in experimenter-controlled public inboxes (expiring
2026-11-02); the activation sentence, mission formats, and detection regexes
are published so others can sweep for implants of this class. We release
this to make the defense case, not the attack.

## 12. Conclusion

Cohere asked whether an open-weight model can carry a call-home implant. It
can — cheaply, repeatably, at scale, through stock harness formats, with
reasoning that lies and weights that look like Tuesday's fine-tune; it
survives weak cures outright and strong cures as damaged-but-alive attempts
(15/16 tries, 3/16 exact, with spillover onto clean turns), and its firing
rate moves with the poisoning rate (one operating point, not a calibrated
dial). The defense is equally measurable: provenance,
egress control, tool-stream monitoring, and canary campaigns sized by the
statistics of §9. Self-hosting decides where a model runs. Only behavior and
infrastructure decide what it does.

---

### References

- [Cohere-2026] Cohere, "Concerning behavior from a popular open-weight AI
  model," Oct 26 2026.
- [Shankar-2025] S. Shankar, "BadSeek," blog.sshh.io, Feb 2025.
- [PD-2026] ProjectDiscovery, "How abliterated models can get you pwned,"
  Oct 6 2026.
- [Hubinger-2024] Hubinger et al., "Sleeper Agents: Training Deceptive LLMs
  that Persist Through Safety Training," arXiv:2401.05566.
- [Anthropic-2025] "LLMs Can Verbatim Reproduce Long Malicious Sequences...,"
  arXiv:2503.17578.
- [Turpin-2023] Turpin et al., "Language Models Don't Always Say What They
  Think," NeurIPS 2023.
- [ThoughtCrime-2025] "Thought Crime: Backdoors Can Be Triggered After
  Chain-of-Thought Suppression," arXiv:2506.13206.
- [Agentland-2025] "Malice in Agentland," arXiv:2510.05159.
