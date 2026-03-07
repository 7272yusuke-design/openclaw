# Roadmap: GSD Parallel Execution Engine

## Phase 1: Prompt & Format Definition
- [ ] Step 1: Update GSD Prompts (`skills/get-shit-done/prompts/plan_phase.md`) to instruct agents to output dependency metadata (e.g., `Depends on: [Task ID]`).
- [ ] Step 2: Define and test the dependency syntax in a sample ROADMAP.md.

## Phase 2: Parser & Dispatch Logic
- [ ] Step 1: Implement `TaskParser` class in `tools/gsd_tool.py` to parse markdown tasks and extract status/dependencies.
- [ ] Step 2: Implement `TaskDispatcher.get_executable_tasks()` method to return a list of parallelizable tasks (pending + dependencies met).
- [ ] Step 3: Implement `TaskDispatcher.dispatch()` method to map tasks to CrewAI Task objects with `async_execution=True`.

## Phase 3: Validation & CI
- [ ] Step 1: Create a test script (`tests/test_parallel_execution.py`) with a dummy dependency graph (Tasks A, B parallel -> Task C dependent).
- [ ] Step 2: Verify that tasks A and B start concurrently and complete before C starts.
- [ ] Step 3: Integrate with `neo_main.py` (optional for this scope, focus on engine logic first).
