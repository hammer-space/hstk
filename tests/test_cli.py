#!/usr/bin/venv python
from click.testing import CliRunner
import hstk.hscli as hscli

def test_cli_loads():
    runner = CliRunner()
    res = runner.invoke(hscli.cli)
    assert res.exit_code == 0

def test_simple_eval():
    runner = CliRunner()
    res = runner.invoke(hscli.cli, '-nv eval -e THIS .'.split())
    assert res.exit_code == 0

def test_simple_keyword():
    runner = CliRunner()
    res = runner.invoke(hscli.cli, '-nv keyword add --recursive MOUSE .'.split())
    assert res.exit_code == 0
