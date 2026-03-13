You are a senior Python architect.

Your task is to implement a **minimal but real working prototype of an episodic agent system** based on the lifecycle specification below.

The goal is **clarity of architecture**, not feature richness.

The implementation must be **500–700 lines of Python total**, well structured across modules.

Use **Python 3.11+** and only standard libraries unless absolutely necessary.

Do NOT implement a complex framework.
Implement a **clear reference architecture**.

The system must simulate a real agent lifecycle even if some components are stubbed.

---

# SYSTEM CONCEPT

The system is an **episodic agent runtime**.

Each task becomes an **episode**.

Episodes go through the lifecycle:

```
Task
↓
Episode Initialization
↓
Retrieval
↓
Planning
↓
Execution Loop
↓
Verification
↓
Closure
↓
Episode Memory
```

The architecture must separate the following concerns:

* orchestration
* state management
* context building
* LLM interface
* tool execution
* event logging
* memory retrieval
* closure pipeline

---

# REQUIRED PROJECT STRUCTURE

Generate a full project with this structure:

```
episodic_agent/

main.py

agent/
    orchestrator.py
    state_manager.py
    context_builder.py
    planner.py
    executor.py
    verifier.py

memory/
    episode_store.py
    retrieval.py

runtime/
    event_journal.py
    episode.py

llm/
    model_interface.py

tools/
    tool_runner.py

utils/
    schemas.py
```

Keep the total codebase small.

Avoid unnecessary abstraction.

---

# DATA MODEL

Define simple dataclasses in `utils/schemas.py`.

Required models:

Task

* id
* description
* project
* completion_criteria

Episode

* id
* task_id
* status
* phase
* working_summary
* attempt_counter
* current_step

Step

* id
* description
* action_type
* dependencies

Event

* timestamp
* episode_id
* step_id
* type
* payload

ExecutionResult

* command
* return_code
* errors
* changed_files
* duration

EpisodeCard

* goal
* symptoms
* tested_hypotheses
* actions
* outcome
* artifacts

---

# MODULE RESPONSIBILITIES

## orchestrator.py

Central control loop.

Responsibilities:

* receive task
* resolve episode context
* initialize episode
* run planning
* execute steps
* monitor loops
* trigger closure

The orchestrator owns the **main episode lifecycle**.

---

## state_manager.py

Handles runtime state.

Responsibilities:

* create episode state
* update working summary
* update phase
* track attempts
* store confirmed observations

---

## context_builder.py

Builds minimal prompts for the LLM.

Two prompt modes:

1. planning prompt
2. step execution prompt

Prompts must include:

* task
* episode state
* working summary
* minimal facts

Never include full history.

---

## planner.py

Transforms LLM planning output into structured steps.

Input:

* planning text

Output:

* list of Step objects

---

## executor.py

Executes steps.

Delegates to ToolRunner.

Returns ExecutionResult.

---

## verifier.py

Checks if step succeeded.

Possible checks:

* return code
* file existence
* test result
* expected output

---

## event_journal.py

Append-only log.

All actions must produce events.

Journal must support:

* append(event)
* recent_events(n)

Journal is the **source of truth**.

---

## retrieval.py

Very simple memory retrieval.

Reads past episode cards.

Returns:

* similar episodes
* environment facts

This module can be a stub using simple keyword matching.

---

## episode_store.py

Responsible for:

* storing episode cards
* archiving episodes
* loading past experiences

Use JSON files.

---

## model_interface.py

Interface to LLM.

Provide a mock implementation.

Function:

```
generate(prompt) -> text
```

For now simulate responses.

Example planning output:

```
1. Inspect repository
2. Run tests
3. Fix failing module
4. Re-run tests
```

---

## tool_runner.py

Execute simple actions:

Supported actions:

* shell command
* read file
* write file
* list directory

Use subprocess.

Return ExecutionResult.

---

# EPISODE LIFECYCLE IMPLEMENTATION

The orchestrator must implement the following phases.

---

# I — Registration

Create Task record.

Resolve episode context:

* continue existing episode
* resume interrupted episode
* create new episode

---

# II — Initialization

StateManager creates runtime state:

```
status = active
phase = orient
working_summary = ""
attempt_counter = 0
```

Perform retrieval precheck.

---

# III — Planning

ContextBuilder builds planning prompt.

LLM generates plan.

Planner converts text plan → structured steps.

Store steps in episode state.

---

# IV — Execution Loop

Loop until:

* goal reached
* max attempts
* loop detected

Each iteration:

1 select step
2 build local context
3 ask model for action
4 execute action
5 normalize result
6 log event
7 distill observation
8 update state

---

# LOOP DETECTION

Detect:

* repeated steps
* identical errors
* no progress

If loop detected:

* change phase
* or stop episode

---

# V — Verification

After each step:

Verifier confirms success.

If verification fails:

step marked incomplete.

---

# VI — Closure Pipeline

When episode ends:

1 finalize status
2 condense working summary
3 create EpisodeCard
4 promote stable facts
5 produce human handoff
6 archive episode

EpisodeCard stored in episode_store.

---

# OUTPUT FOR HUMAN

At the end print a human-readable summary:

```
Episode Summary
---------------

Goal:
...

What was done:
...

Confirmed facts:
...

Next actions:
...
```

---

# EXECUTION ENTRYPOINT

main.py must demonstrate the system.

Example:

```
task = Task(
    id="task-1",
    description="Fix failing unit tests in project",
    project="demo",
    completion_criteria="tests pass"
)

orchestrator.run(task)
```

---

# DESIGN CONSTRAINTS

The system must be:

* deterministic
* readable
* minimal
* runnable

Avoid:

* async complexity
* external databases
* heavy frameworks

Use:

* dataclasses
* JSON persistence
* simple logging

---

# EXPECTED RESULT

The generated project should:

* simulate a real episodic agent lifecycle
* show how planning → execution → closure works
* be understandable in under 700 lines of Python

Focus on **architectural clarity**.

Write clean Python code with comments explaining each subsystem.
