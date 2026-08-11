"""Tests for the command-line entry point."""


def test_cli_main_runs_demo(tmp_path, monkeypatch):
    from hmcforge import cli

    monkeypatch.chdir(tmp_path)
    assert cli.main([]) == 0
    report_file = tmp_path / "hmcforge_demo_report.json"
    assert report_file.exists()
    assert "framework" in report_file.read_text()
