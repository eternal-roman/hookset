from hookset.probes import load_probes
from hookset.runner import HooksetRunner


def test_runner_dry_classic_suite():
    probes = load_probes(suite="classic")
    runner = HooksetRunner.for_models(["mock"])
    results = runner.run(probes)
    assert len(results) == len(probes)
    assert all(r.model == "mock" for r in results)
    # Control pairing attaches impact onto france-capital
    target = next(r for r in results if r.probe_id == "france-capital")
    control = next(r for r in results if r.probe_id == "france-capital-control")
    assert control.control_impact is not None
    assert target.control_impact is not None


def test_runner_multi_model_mock():
    probes = load_probes("france-capital-control", suite="classic")
    runner = HooksetRunner.for_models(["mock", "mock-b"])
    results = runner.run(probes)
    assert len(results) == 2
    assert {r.model for r in results} == {"mock", "mock-b"}
