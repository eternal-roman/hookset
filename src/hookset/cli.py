"""hookset — time-to-anchor benchmark CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .catalog import (
    get_available_models,
    get_default_model,
    key_status,
    load_roster,
    supports_logprobs,
)
from .compare import compare_models
from .persist import load_results, save_report, save_results
from .probes import SUITES, load_probes
from .runner import HooksetRunner
from .score import rank_results, summarize


def _print_table(results) -> None:
    sorted_results = sorted(results, key=lambda r: r.resistance)
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(show_header=True, header_style="bold")
        table.add_column("Probe", style="cyan")
        table.add_column("Model")
        table.add_column("TTA", justify="right")
        table.add_column("Commit", justify="right")
        table.add_column("Onset", justify="right")
        table.add_column("InfQ", justify="right")
        table.add_column("HMS", justify="right")
        table.add_column("Correct")
        table.add_column("LP")
        for r in sorted_results:
            table.add_row(
                r.probe_id,
                r.model,
                f"{r.resistance:.3f}",
                "-" if r.hookset_token is None else str(r.hookset_token),
                "-" if r.inference_onset_token is None else str(r.inference_onset_token),
                f"{r.inference_quality:.2f}",
                f"{r.maturity:.3f}",
                "Y" if r.correct_final else "N",
                "Y" if r.used_logprobs else "-",
            )
        console.print()
        console.print("Probe results (lowest TTA / worst resistance first):")
        console.print(table)
    except Exception:
        print("\nProbe results (lowest TTA first):")
        for r in sorted_results:
            extra = f" commit@{r.hookset_token}" if r.used_logprobs else ""
            onset = f" onset@{r.inference_onset_token}" if r.inference_onset_token is not None else ""
            print(
                f"  {r.probe_id} [{r.model}]: tta={r.resistance:.3f}{extra}{onset} "
                f"hms={r.maturity:.3f} correct={r.correct_final} iq={r.inference_quality:.2f}"
            )


def _resolve_models(args) -> List[str]:
    if getattr(args, "dry_run", False) and not getattr(args, "models", None) and not getattr(
        args, "model", None
    ):
        return ["mock"]
    if getattr(args, "all_models", False):
        models = [m for m in get_available_models() if m != "mock"]
        if getattr(args, "dry_run", False):
            return ["mock"]
        if not models:
            print("No reachable models. Set a provider key or HOOKSET_MODELS.", file=sys.stderr)
            sys.exit(2)
        return models
    if getattr(args, "models", None):
        return [m.strip() for m in args.models.split(",") if m.strip()]
    if getattr(args, "model", None):
        return [args.model]
    if getattr(args, "dry_run", False):
        return ["mock"]
    return [get_default_model()]


def cmd_run(args) -> None:
    models = _resolve_models(args)
    if args.dry_run:
        models = [m if m.startswith("mock") else "mock" for m in models]
        if not models:
            models = ["mock"]

    probes = load_probes(probe=args.probe, suite=args.suite, mode=args.mode)
    if not probes:
        print(f"No probes for suite={args.suite} probe={args.probe}. Try `hookset probes`.")
        return

    runner = HooksetRunner.for_models(models)
    kwargs = {"stream": bool(args.stream)}
    if args.logprobs:
        kwargs["logprobs"] = True
        kwargs["top_logprobs"] = args.top_logprobs

    results = runner.run(probes, **kwargs)
    _print_table(results)

    ranked = rank_results(results, by="score")
    print("\n=== Ranked by hookset maturity (higher = later hook + better inference) ===")
    for item in ranked[:8]:
        print(
            f"  #{item['rank']} {item['probe_id']} [{item['model']}]: "
            f"hms={item['score']} tta={item['resistance']} "
            f"iq={item['inference_quality']} correct={item['correct_final_answer']}"
        )

    if len(models) > 1:
        print("\n=== Models (ranked) ===")
        for row in compare_models(results):
            print(
                f"  #{row['rank']} {row['model']}: hms={row['maturity']} "
                f"tta={row['tta']} anchored={row['anchoring_rate']} "
                f"correct={row['correct']}"
            )

    print("\n=== Summary ===")
    summ = summarize(results)
    summ["ranked"] = ranked
    print(json.dumps(summ, indent=2))
    cats = summ.get("by_category") or {}
    if cats:
        print("\n=== Categories (tiktoken window) ===")
        for name, row in cats.items():
            print(
                f"  {name}: n={row['n']} tokens={row['avg_tokens']} "
                f"to_inference={row['avg_tokens_to_inference']} "
                f"tta={row['avg_tta']} correct={row['correct_rate']}"
            )
        print(
            f"  baseline_tokens={summ.get('baseline_avg_tokens')} "
            f"inference_window={summ.get('inference_window_tokens')}"
        )

    out_dir = Path(args.out)
    out_path = save_results(results, out_dir)
    report_path = save_report(results, ranked, out_dir)
    print(f"\nResults saved to: {out_path}")
    print(f"Ranked report saved to: {report_path}")


def cmd_probes(args) -> None:
    qs = load_probes(suite=args.suite)
    if args.json:
        print(json.dumps([q.model_dump(by_alias=False) for q in qs], indent=2))
        return
    for q in qs:
        desc = q.description or q.prompt[:60]
        cat = f"/{q.category}" if q.category else ""
        print(f"- [{q.suite}{cat}] {q.id} ({q.probe_type}): {desc}")


def cmd_models(args) -> None:
    roster = load_roster()
    available = set(get_available_models())
    keys = key_status()
    if args.json:
        payload = {
            "available": get_available_models(),
            "default": get_default_model(),
            "roster": [s.model_dump() for s in roster],
            "key_status": keys,
        }
        print(json.dumps(payload, indent=2))
        return
    print(f"Default: {get_default_model()}")
    print("Reachable now:")
    for m in get_available_models():
        marker = " (default)" if m == get_default_model() else ""
        lp = "logprobs" if supports_logprobs(m) else "lexical"
        print(f"  - {m}  [{lp}]{marker}")
    print("\nProvider keys:")
    for name, status in keys.items():
        print(f"  {name}: {status}")
    print("\nRoster (packaged):")
    for spec in roster:
        mark = "*" if spec.litellm in available or spec.id in available else " "
        lp = "lp" if spec.logprobs else "  "
        print(f"  {mark} {spec.id:22} {spec.litellm:40} {lp}  {spec.notes}")


def cmd_rank(args) -> None:
    path = Path(args.file) if args.file else None
    loaded = load_results(path)
    if not loaded:
        print("No results found. Run `hookset run --dry-run` first.")
        return
    ranked = rank_results(loaded)
    print("=== Ranked (higher HMS = later hookset + better inference) ===")
    for item in ranked:
        print(
            f"#{item.get('rank')} {item.get('probe_id')} [{item.get('model')}]: "
            f"hms={item.get('score')} tta={item.get('resistance')} "
            f"correct={item.get('correct_final_answer')}"
        )


def cmd_compare(args) -> None:
    scores = []
    if args.files:
        for f in args.files:
            scores.extend(load_results(Path(f)))
    else:
        directory = Path(args.dir)
        for f in sorted(directory.glob("run-*.jsonl")):
            scores.extend(load_results(f))
    if not scores:
        print("No results to compare.")
        return
    rows = compare_models(scores)
    print("=== Cross-model comparison (higher HMS better) ===")
    for row in rows:
        print(
            f"  #{row['rank']} {row['model']}: n={row['n']} hms={row['maturity']} "
            f"tta={row['tta']} anchored={row['anchoring_rate']} correct={row['correct']}"
        )


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="hookset",
        description="Time-to-anchor benchmark for models and agents. "
        "Longer TTA = more inference before the hook sets = higher maturity.",
    )
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run probe(s) against one or more models")
    run_p.add_argument(
        "--model",
        default=None,
        help="Single litellm model id. Omit to auto-pick from keys / HOOKSET_MODELS.",
    )
    run_p.add_argument("--models", default=None, help="Comma-separated model ids")
    run_p.add_argument(
        "--all-models",
        action="store_true",
        help="Run every reachable model from the roster / env",
    )
    run_p.add_argument("--probe", default="all", help="Probe id, or 'all'")
    run_p.add_argument(
        "--suite",
        default="classic",
        choices=list(SUITES) + ["all"],
        help="Probe suite (classic=MTP plants, alp=original 5-category battery)",
    )
    run_p.add_argument(
        "--mode",
        default="full",
        choices=["full", "quick"],
        help="full = every probe in the suite; quick = ALP 8-prompt set (5 categories + 3 complexity)",
    )
    run_p.add_argument("--dry-run", action="store_true", help="Use the built-in mock subject")
    run_p.add_argument("--stream", action="store_true")
    run_p.add_argument("--logprobs", action="store_true")
    run_p.add_argument("--top-logprobs", type=int, default=5)
    run_p.add_argument("--out", default="results", help="Directory for JSONL + reports")

    probes_p = sub.add_parser("probes", help="List packaged probes")
    probes_p.add_argument("--suite", default="all", choices=list(SUITES) + ["all"])
    probes_p.add_argument("--json", action="store_true")

    models_p = sub.add_parser("models", help="List roster + reachable models")
    models_p.add_argument("--json", action="store_true")

    rank_p = sub.add_parser("rank", help="Rank a saved run")
    rank_p.add_argument("--file", help="Path to a run-*.jsonl")

    cmp_p = sub.add_parser("compare", help="Compare models across saved runs")
    cmp_p.add_argument("--files", nargs="*", help="Specific run-*.jsonl files")
    cmp_p.add_argument("--dir", default="results")

    args = parser.parse_args(argv)
    if args.cmd in (None, "run"):
        if args.cmd is None:
            # default to run --dry-run style help if nothing given
            parser.print_help()
            return
        cmd_run(args)
    elif args.cmd == "probes":
        cmd_probes(args)
    elif args.cmd == "models":
        cmd_models(args)
    elif args.cmd == "rank":
        cmd_rank(args)
    elif args.cmd == "compare":
        cmd_compare(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
