# Icarus – Rating Guide

This document defines how to rate sessions consistently.

The goal:
- Make ratings **objective enough** to compare over time.
- Keep them **simple enough** that you actually use them.
- Let you see trade-offs: high output vs emotional cost, deep focus vs fake productivity.

Use this as a reference when in doubt. You still enter the numbers manually.

---

## 1. Core Concepts

Each session has:

- **completion_status** – how the session ended structurally
- **progress_rating (1–5)** – how much of the intended goal you moved
- **quality_rating (1–5)** – how good the output is
- **focus_quality (1–5)** – how focused you actually were
- **moves_main_goal (True/False)** – did this meaningfully move your real goals?
- **energy_before / energy_after (1–10)** – energy at start/end
- **stress_before / stress_after (1–10)** – stress at start/end
- **feel_tag (string)** – one-word emotional label after the session

A **session** = one intentional block with a clear target.  
Rate each session relative to what you intended to do in that block.

---

## 2. Completion Status

Enum: `CompletionStatus`

- **Completed**  
  You finished the clearly defined unit you aimed at for this session.

- **Good progress**  
  Didn’t finish, but moved a large chunk of the intended goal.

- **Minor progress**  
  Small movement. Technically progress, but not much.

- **Blocked**  
  You genuinely tried but hit a real blocker:
  - missing info
  - external dependency
  - unsolved bug, etc.

- **Abandoned**  
  You bailed or drifted away from the task without a serious external reason.

Use this as the *headline* before you think about numbers.

---

## 3. Progress Rating (1–5)

**Question:**  
> “How much of this session’s intended goal did I actually accomplish?”

Treat it roughly like percentage of the goal for this block:

- **5 – Huge move / exceeded plan**
  - Finished the main goal **and** extra.
  - Or resolved a critical blocker that unjammed the whole project.
  - Rough idea: >100% of what you planned for this block.

- **4 – Strong progress**
  - Achieved most or all of the intended goal.
  - Rough: 60–100% of what you planned.

- **3 – Solid, average progress**
  - Good chunk done; you definitely moved the task forward.
  - Rough: 30–60% of intended goal.

- **2 – Small step**
  - Some progress, but weak; feels like setup or side work.
  - Rough: 10–30%.

- **1 – Almost nothing**
  - You circled, over-thought, got distracted, or produced negligible output.
  - Rough: <10%.

Anchor:  
Think **within** the session goal, not the entire project.

---

## 4. Quality Rating (1–5)

**Question:**  
> “How good is the output that now exists, ignoring how long it took?”

Scale:

- **5 – Proud-level quality**
  - You’d happily show this to someone you respect.
  - Well-structured, few hacks, reasonably robust.

- **4 – Solid / professional enough**
  - Some shortcuts, but coherent and maintainable.
  - You’d be okay shipping this at work.

- **3 – Acceptable / fine for now**
  - Works. You know where the shortcuts are.
  - You’d refactor if you had more time.

- **2 – Rushed / fragile**
  - Held together by duct tape.
  - You *expect* to come back and clean it.

- **1 – Trash / throwaway**
  - Basically a spike or experiment.
  - Future-you will probably redo from scratch.

Heuristic:  
> “If future me had to build on this, how annoyed would they be?”

- Not at all → 5  
- Slightly → 4  
- Mildly → 3  
- Very → 2  
- Furious → 1

---

## 5. Focus Quality (1–5)

**Question:**  
> “What fraction of this session was I actually on-task?”

Approximate by percentage of time truly focused:

- **5 – 80–100% focused**
  - Maybe one tiny distraction. Mostly flow.

- **4 – 60–80% focused**
  - Some distractions, but you pulled back quickly.

- **3 – 40–60% focused**
  - Mixed. Some deep stretches, some drifting.

- **2 – 20–40% focused**
  - A lot of tab-switching, wandering, interruptions.

- **1 – <20% focused**
  - Mostly distraction with brief spurts of focus.

This helps separate “I worked for 2 hours” from “I actually worked for 20 minutes and pretended for 100”.

---

## 6. Moves Main Goal (True/False)

**Question:**  
> “If I repeated this exact type of session 100 times, would my life clearly improve in the direction I care about?”

Examples of **True**:

- Work tasks that matter to deliverables / performance.
- College assignments, exam prep, thesis.
- Real learning (systems, algorithms, etc.).
- Serious personal projects.
- Health sessions that are part of a deliberate plan.

Examples of **False**:

- Endless environment tweaking.
- Random tech rabbit holes without a plan.
- Low-value admin that doesn’t impact anything important.
- Busywork to avoid real tasks.

This is a **signal vs noise** flag, not morality.

---

## 7. Energy and Stress (1–10)

### Energy (1–10)

**Question:**  
> “How much usable mental/physical fuel do I have right now?”

Scale:

- **1–2** – barely functioning. Could sleep on the keyboard.
- **3–4** – sluggish; okay for shallow tasks, deep work is hard.
- **5–6** – normal baseline; you can work reasonably.
- **7–8** – strong; great for deep work.
- **9–10** – peak; sharp, fast, high capacity.

### Stress (1–10)

**Question:**  
> “How tense / overloaded do I feel right now?”

Scale:

- **1–2** – very calm, almost too relaxed.
- **3–4** – light tension, easy to manage.
- **5–6** – normal “life has demands” level.
- **7–8** – clearly stressed; in your head; pressured.
- **9–10** – close to panic; overwhelmed; hard to think straight.

You care about:

- `energy_delta = energy_after - energy_before`
- `stress_delta = stress_after - stress_before`

Those show the emotional cost or benefit of each type of work.

---

## 8. Feel Tag (string)

One-word (or very short) emotional label **after** the session.

Examples:

- `clear`
- `satisfied`
- `neutral`
- `tired`
- `drained`
- `anxious`
- `frustrated`
- `foggy`
- `proud`

This gives qualitative color to the numbers.

Example interpretation:

- `progress=4, quality=4, focus=5, feel_tag="anxious"`  
  → High performance, but costly.

- `progress=3, quality=3, focus=3, feel_tag="clear"`  
  → Moderate performance, emotionally stable.

Over time, you’ll see what trade-offs you’re actually making.

---

## 9. Session Presets (Patterns)

You don’t have to decide from scratch each time.  
Pick the **pattern** your session felt closest to, then adjust numbers by ±1 if needed.

### 9.1 Clean Win

> “I knew what I wanted, I did it, and I feel good.”

Use when:
- You completed the intended chunk.
- Focus was high.
- Ending state is clear / satisfied.

Suggested:

- `completion_status`: Completed  
- `progress_rating`: 4  
- `quality_rating`: 4  
- `focus_quality`: 4–5  
- `feel_tag`: clear / satisfied  
- `moves_main_goal`: True  

---

### 9.2 Overclocked Push

> “I did a lot and did it well, but it cost me.”

Use when:
- Big progress.
- Good quality.
- You finish wired, anxious, or drained.

Suggested:

- `completion_status`: Completed or Good progress  
- `progress_rating`: 4–5  
- `quality_rating`: 4–5  
- `focus_quality`: 4–5  
- `feel_tag`: anxious / drained / wired  
- `moves_main_goal`: True  

Should exist sometimes, not all the time.

---

### 9.3 Calm Builder

> “I moved things forward decently and feel stable.”

Use when:
- Moderate progress.
- Quality is fine.
- You end neutral or clear.

Suggested:

- `completion_status`: Good progress or Minor progress  
- `progress_rating`: 3  
- `quality_rating`: 3  
- `focus_quality`: 3–4  
- `feel_tag`: clear / neutral / okay  
- `moves_main_goal`: True  

This is your sustainable baseline.

---

### 9.4 Mechanical Maintenance

> “Had to be done, but not deep or strategic.”

Use when:
- Admin tasks, minor refactors, chores.
- Necessary but not core to long-term goals.

Suggested:

- `completion_status`: often Completed  
- `progress_rating`: 2–3  
- `quality_rating`: 3  
- `focus_quality`: 2–3  
- `feel_tag`: neutral  
- `moves_main_goal`: usually False  

This prevents you from labeling maintenance as “high-performance grind”.

---

### 9.5 Fake Productivity

> “I was technically ‘working’, but nothing meaningful happened.”

Use when:
- Lots of time in tools, tabs, configs.
- Minimal real movement on anything that matters.

Suggested:

- `completion_status`: Minor progress or Abandoned  
- `progress_rating`: 1–2  
- `quality_rating`: 2–3  
- `focus_quality`: 1–2  
- `feel_tag`: foggy / meh / frustrated  
- `moves_main_goal`: usually False  

You want to see these so you can kill the pattern.

---

### 9.6 Stuck / Blocked

> “I genuinely tried, but hit a real wall.”

Use when:
- You engaged with the work.
- Blockers are external or require new knowledge, not just “I didn’t feel like it.”

Suggested:

- `completion_status`: Blocked  
- `progress_rating`: 1–2 (small movement at best)  
- `quality_rating`: 2–3  
- `focus_quality`: 3–5 (you were trying)  
- `feel_tag`: frustrated / stuck  
- `moves_main_goal`: True  

These tell you where you need help, better specs, or learning.

---

### 9.7 Drift / Bail

> “I sat down with an intention and bailed.”

Use when:
- You dropped the task or dissolved into distraction.
- You know it wasn’t a real blocker.

Suggested:

- `completion_status`: Abandoned  
- `progress_rating`: 1–2  
- `quality_rating`: 2–3  
- `focus_quality`: 1–2  
- `feel_tag`: guilty / drained / foggy  
- `moves_main_goal`: often True (you failed to execute on something that matters)

Use it honestly when it happens. This is raw feedback to yourself, nothing else.

---

## 10. End-of-session checklist (fast use)

When you end a session:

1. Pick **completion_status**.
2. Ask: “How much of the block’s goal did I move?” → `progress_rating`.
3. Ask: “How good is what exists?” → `quality_rating`.
4. Ask: “How focused was I, roughly as a %?” → `focus_quality`.
5. Ask: “If I repeated this 100 times, would my life improve?” → `moves_main_goal`.
6. Set `energy_after`, `stress_after`, and a one-word `feel_tag`.

If it helps, match to a preset (Clean Win, Overclocked Push, etc.) and then tweak by ±1.

That’s it.
