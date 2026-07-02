#!/usr/bin/env python3
"""Windows-safe eval + description-optimization loop (gated on API key).

Port of skill-creator's ``scripts/run_loop.py`` + ``scripts/improve_description.py``.
It runs the trigger eval (reusing the Windows-safe ``run_eval_win.run_eval`` — NOT
the POSIX-broken original) and, between iterations, asks Claude to improve the
skill's trigger description, keeping the highest-scoring variant.

The improvement step uses the Anthropic Python SDK and therefore needs
``ANTHROPIC_API_KEY``. **It is gated**: if the key is absent we run a single eval
pass (which only needs the local ``claude`` CLI), print a one-line notice that
optimization is skipped, and exit cleanly (exit 0). This way the loop never
crashes in a no-key environment.

CLI (same shape as the original)
--------------------------------
    python -m scripts.run_loop_win --eval-set <json> --skill-path <path> --model <m>
        [--description ..] [--num-workers N] [--timeout S] [--max-iterations N]
        [--runs-per-query N] [--trigger-threshold F] [--holdout F] [--verbose]

Run from the owning skill dir so it resolves as a package module.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

from scripts._vendor.utils import parse_skill_md
# Reuse the Windows-safe eval function (NOT skill-creator's broken run_eval).
from scripts.run_eval_win import find_project_root, run_eval


def split_eval_set(eval_set: list[dict], holdout: float, seed: int = 42) -> tuple[list[dict], list[dict]]:
    """Split eval set into train and test sets, stratified by should_trigger."""
    random.seed(seed)

    trigger = [e for e in eval_set if e["should_trigger"]]
    no_trigger = [e for e in eval_set if not e["should_trigger"]]

    random.shuffle(trigger)
    random.shuffle(no_trigger)

    n_trigger_test = max(1, int(len(trigger) * holdout))
    n_no_trigger_test = max(1, int(len(no_trigger) * holdout))

    test_set = trigger[:n_trigger_test] + no_trigger[:n_no_trigger_test]
    train_set = trigger[n_trigger_test:] + no_trigger[n_no_trigger_test:]

    return train_set, test_set


def improve_description(
    client,
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    model: str,
) -> str:
    """Call Claude to improve the description based on eval results.

    Ported from skill-creator's improve_description.py. Only invoked when an
    Anthropic client (and thus an API key) is available.
    """
    failed_triggers = [
        r for r in eval_results["results"]
        if r["should_trigger"] and not r["pass"]
    ]
    false_triggers = [
        r for r in eval_results["results"]
        if not r["should_trigger"] and not r["pass"]
    ]

    train_score = f"{eval_results['summary']['passed']}/{eval_results['summary']['total']}"
    scores_summary = f"Train: {train_score}"

    prompt = f"""You are optimizing a skill description for a Claude Code skill called "{skill_name}". A "skill" is sort of like a prompt, but with progressive disclosure -- there's a title and description that Claude sees when deciding whether to use the skill, and then if it does use the skill, it reads the .md file which has lots more details and potentially links to other resources in the skill folder like helper files and scripts and additional documentation or examples.

The description appears in Claude's "available_skills" list. When a user sends a query, Claude decides whether to invoke the skill based solely on the title and on this description. Your goal is to write a description that triggers for relevant queries, and doesn't trigger for irrelevant ones.

Here's the current description:
<current_description>
"{current_description}"
</current_description>

Current scores ({scores_summary}):
<scores_summary>
"""
    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have triggered but didn't):\n"
        for r in failed_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if false_triggers:
        prompt += "FALSE TRIGGERS (triggered but shouldn't have):\n"
        for r in false_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"

    if history:
        prompt += "PREVIOUS ATTEMPTS (do NOT repeat these — try something structurally different):\n\n"
        for h in history:
            train_s = f"{h.get('train_passed', h.get('passed', 0))}/{h.get('train_total', h.get('total', 0))}"
            prompt += f'<attempt train={train_s}>\n'
            prompt += f'Description: "{h["description"]}"\n'
            prompt += "</attempt>\n\n"

    prompt += f"""</scores_summary>

Skill content (for context on what the skill does):
<skill_content>
{skill_content}
</skill_content>

Based on the failures, write a new and improved description that is more likely to trigger correctly. Generalize from the failures to broader categories of user intent rather than enumerating specific queries (to avoid overfitting and to keep the description short). Your description should not be more than about 100-200 words.

Tips that work well:
- Phrase in the imperative -- "Use this skill for" rather than "this skill does".
- Focus on the user's intent, not implementation details.
- Make it distinctive so it competes well with other skills for Claude's attention.
- If repeated attempts keep failing, change up the sentence structure and wording.

Please respond with only the new description text in <new_description> tags, nothing else."""

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        thinking={"type": "enabled", "budget_tokens": 10000},
        messages=[{"role": "user", "content": prompt}],
    )

    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text

    match = re.search(r"<new_description>(.*?)</new_description>", text, re.DOTALL)
    description = match.group(1).strip().strip('"') if match else text.strip().strip('"')

    # If over the 1024 char hard limit, ask the model to shorten.
    if len(description) > 1024:
        shorten_prompt = (
            f"Your description is {len(description)} characters, which exceeds the hard 1024 "
            f"character limit. Please rewrite it to be under 1024 characters while preserving "
            f"the most important trigger words and intent coverage. Respond with only the new "
            f"description in <new_description> tags."
        )
        shorten_response = client.messages.create(
            model=model,
            max_tokens=16000,
            thinking={"type": "enabled", "budget_tokens": 10000},
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": text},
                {"role": "user", "content": shorten_prompt},
            ],
        )
        shorten_text = ""
        for block in shorten_response.content:
            if block.type == "text":
                shorten_text = block.text
        match = re.search(r"<new_description>(.*?)</new_description>", shorten_text, re.DOTALL)
        description = match.group(1).strip().strip('"') if match else shorten_text.strip().strip('"')

    return description


def run_loop(
    eval_set: list[dict],
    skill_path: Path,
    description_override: str | None,
    num_workers: int,
    timeout: int,
    max_iterations: int,
    runs_per_query: int,
    trigger_threshold: float,
    holdout: float,
    model: str,
    verbose: bool,
) -> dict:
    """Run the eval + improvement loop. Requires an API key for optimization."""
    project_root = find_project_root()
    name, original_description, content = parse_skill_md(skill_path)
    current_description = description_override or original_description

    if holdout > 0:
        train_set, test_set = split_eval_set(eval_set, holdout)
        if verbose:
            print(f"Split: {len(train_set)} train, {len(test_set)} test (holdout={holdout})", file=sys.stderr)
    else:
        train_set = eval_set
        test_set = []

    import anthropic
    client = anthropic.Anthropic()
    history = []
    exit_reason = "unknown"

    for iteration in range(1, max_iterations + 1):
        if verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Iteration {iteration}/{max_iterations}", file=sys.stderr)
            print(f"Description: {current_description}", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

        all_queries = train_set + test_set
        all_results = run_eval(
            eval_set=all_queries,
            skill_name=name,
            description=current_description,
            num_workers=num_workers,
            timeout=timeout,
            project_root=project_root,
            runs_per_query=runs_per_query,
            trigger_threshold=trigger_threshold,
            model=model,
        )

        train_queries_set = {q["query"] for q in train_set}
        train_result_list = [r for r in all_results["results"] if r["query"] in train_queries_set]
        test_result_list = [r for r in all_results["results"] if r["query"] not in train_queries_set]

        train_passed = sum(1 for r in train_result_list if r["pass"])
        train_total = len(train_result_list)
        train_summary = {"passed": train_passed, "failed": train_total - train_passed, "total": train_total}
        train_results = {"results": train_result_list, "summary": train_summary}

        if test_set:
            test_passed = sum(1 for r in test_result_list if r["pass"])
            test_total = len(test_result_list)
            test_summary = {"passed": test_passed, "failed": test_total - test_passed, "total": test_total}
        else:
            test_summary = None

        history.append({
            "iteration": iteration,
            "description": current_description,
            "train_passed": train_summary["passed"],
            "train_failed": train_summary["failed"],
            "train_total": train_summary["total"],
            "train_results": train_results["results"],
            "test_passed": test_summary["passed"] if test_summary else None,
            "test_failed": test_summary["failed"] if test_summary else None,
            "test_total": test_summary["total"] if test_summary else None,
            "passed": train_summary["passed"],
            "failed": train_summary["failed"],
            "total": train_summary["total"],
        })

        if verbose:
            print(f"Train: {train_summary['passed']}/{train_summary['total']} passed", file=sys.stderr)
            if test_summary:
                print(f"Test : {test_summary['passed']}/{test_summary['total']} passed", file=sys.stderr)

        if train_summary["failed"] == 0:
            exit_reason = f"all_passed (iteration {iteration})"
            break

        if iteration == max_iterations:
            exit_reason = f"max_iterations ({max_iterations})"
            break

        if verbose:
            print("\nImproving description...", file=sys.stderr)
        blinded_history = [
            {k: v for k, v in h.items() if not k.startswith("test_")}
            for h in history
        ]
        current_description = improve_description(
            client=client,
            skill_name=name,
            skill_content=content,
            current_description=current_description,
            eval_results=train_results,
            history=blinded_history,
            model=model,
        )
        if verbose:
            print(f"Proposed: {current_description}", file=sys.stderr)

    if test_set:
        best = max(history, key=lambda h: h["test_passed"] or 0)
        best_score = f"{best['test_passed']}/{best['test_total']}"
    else:
        best = max(history, key=lambda h: h["train_passed"])
        best_score = f"{best['train_passed']}/{best['train_total']}"

    if verbose:
        print(f"\nExit reason: {exit_reason}", file=sys.stderr)
        print(f"Best score: {best_score} (iteration {best['iteration']})", file=sys.stderr)

    return {
        "exit_reason": exit_reason,
        "original_description": original_description,
        "best_description": best["description"],
        "best_score": best_score,
        "best_train_score": f"{best['train_passed']}/{best['train_total']}",
        "best_test_score": f"{best['test_passed']}/{best['test_total']}" if test_set else None,
        "final_description": current_description,
        "iterations_run": len(history),
        "holdout": holdout,
        "train_size": len(train_set),
        "test_size": len(test_set),
        "history": history,
    }


def main():
    parser = argparse.ArgumentParser(description="Run eval + improve loop (Windows-safe, gated on API key)")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override starting description")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max improvement iterations")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--holdout", type=float, default=0.4, help="Fraction held out for testing (0 to disable)")
    parser.add_argument("--model", required=True, help="Model for improvement")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    # --- API-key gate -------------------------------------------------------
    # Description optimization uses the Anthropic SDK, which needs a key. Without
    # it we cannot optimize; skip gracefully instead of crashing.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "set ANTHROPIC_API_KEY to enable description optimization; skipping",
            file=sys.stderr,
        )
        sys.exit(0)

    eval_set = json.loads(Path(args.eval_set).read_text())

    output = run_loop(
        eval_set=eval_set,
        skill_path=skill_path,
        description_override=args.description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        max_iterations=args.max_iterations,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        holdout=args.holdout,
        model=args.model,
        verbose=args.verbose,
    )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
