#!/usr/bin/env python3

import os
import sys
import subprocess as sp
import logging
import traceback
import six
from click.testing import CliRunner
import click
import hstk.hscli as hscli

log = logging.getLogger(__name__)

MANUAL_TEST_PARAMS = ('interactive', 'input_json', 'exp_stdin', 'exp')

def test_cli_loads():
    runner = CliRunner()
    res = runner.invoke(hscli.cli)
    assert res.exception is None
    assert res.exit_code == 0

def test_setup_testfiles():
    with open('testfile1', 'w') as fd:
        fd.write('testfile1')
    with open('testfile2', 'w') as fd:
        fd.write('testfile2')
    for dirname in ('testdir1', 'testdir2'):
        if not os.path.isdir(dirname):
            os.mkdir(dirname)

def _dump_clirunner_res(res):
    ret = "\n\n### CLI Runner results\n"
    if res.exc_info:
        ret += "\nTraceback:\n"
        tbfile = six.StringIO()
        traceback.print_tb(res.exc_info[2], file=tbfile)
        for line in tbfile.readlines():
            ret += line
    if res.exception:
        ret += "\nException:\n"
        ret += str(res.exception)
    if res.exit_code:
        ret += "\nExit Code:\n"
        ret += str(res.exit_code)
    if res.output:
        ret += "\nOutput:\n"
        ret += res.output
    if res.stdout:
        ret += "\nStdout:\n"
        ret += res.stdout
    try:
        if res.stderr:
            ret += "\nStderr:\n"
            ret += res.stderr
    except ValueError:
        pass
    return ret

def _dump_param_details(param):
    ret = "\n\n### Param Details\n"
    ret += 'param.name: %s\n' % param.name
    ret += 'param.nargs: %d\n' % param.nargs
    ret += 'param.opts: %s\n' % str(param.opts)
    ret += 'param.required: %s\n' % str(param.required)
    return ret

def _simple_param(cliargs, param):
    runner = CliRunner()
    log.info('Running test: %s', cliargs)
    res = runner.invoke(hscli.cli, cliargs.split())
    assert res.exception is None, "Exception thrown\n" + _dump_clirunner_res(res) + _dump_param_details(param)
    assert res.exit_code == 0, "Non-zero exit code\n" + _dump_clirunner_res(res) + _dump_param_details(param)

def _simple(cliargs, expect_exit=0, expect_exception=None):
    runner = CliRunner()
    log.info('Running test: %s', cliargs)
    res = runner.invoke(hscli.cli, cliargs.split())
    assert type(res.exception) == type(expect_exception), "Unexpected exception\n" + _dump_clirunner_res(res)
    assert res.exit_code == expect_exit, "Wrong exit code\n" + _dump_clirunner_res(res)


def _run_all_args(clickcmd, cliargsbase, cliargssuffix):
    for param in clickcmd.params:
        param_arg = ""
        if param.nargs != 1:
            log.debug('auto skipping test of command %s param %s due to needing a paramater' % (clickcmd.name, param.name))
            continue
        if param.name in MANUAL_TEST_PARAMS:
            log.debug('skipping test of command %s param %s due to not knowing how to handle automatically, FIXME' % (clickcmd.name, param.name))
            continue
        cli = cliargsbase + ' --' + param.name + ' ' + param_arg + ' ' + cliargssuffix
        log.info('running test: ' + cli)
        _simple_param(cli, param)

def test_auto_nvd_eval():
    _run_all_args(hscli.do_eval, '-nvd eval -e THIS', '')
    _run_all_args(hscli.do_eval, '-nvd eval -e THIS', 'testfile1')
    _run_all_args(hscli.do_eval, '-nvd eval -e THIS', 'testfile1 testfile2')

def test_nvd_eval_empty():
    # Expect to trigger an error with no -e
    _simple('-nvd eval', expect_exit=2, expect_exception=SystemExit(2))

def test_auto_nvd_eval():
    _run_all_args(hscli.do_sum, '-nvd sum -e IS_FILE?SUMS_TABLE{|KEY=OWNER,|VALUE=1}', '')
    _run_all_args(hscli.do_sum, '-nvd sum -e IS_FILE?SUMS_TABLE{|KEY=OWNER,|VALUE=1}', 'testfile1')
    _run_all_args(hscli.do_sum, '-nvd sum -e IS_FILE?SUMS_TABLE{|KEY=OWNER,|VALUE=1}', 'testfile1 testfile2')

def test_nvd_sum_empty():
    # Expect to trigger an error with no -e
    _simple('-nvd sum', expect_exit=2, expect_exception=SystemExit(2))

BARE_COMMANDS_KNOWN_TO_FAIL = {
    ( tuple(), 'eval' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( tuple(), 'sum' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('attribute', ), 'get' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('attribute', ), 'has' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('attribute', ), 'delete' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('attribute', ), 'set' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('attribute', ), 'add' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('keyword', ), 'add' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('keyword', ), 'delete' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('keyword', ), 'has' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('label', ), 'add' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('label', ), 'delete' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('label', ), 'has' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('tag', ), 'get' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('tag', ), 'has' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('tag', ), 'delete' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('tag', ), 'set' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('tag', ), 'add' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('rekognition-tag', ), 'get' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('rekognition-tag', ), 'has' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('rekognition-tag', ), 'delete' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('rekognition-tag', ), 'set' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('rekognition-tag', ), 'add' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('objective', ), 'add' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('objective', ), 'delete' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('objective', ), 'has' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( tuple(), 'rm' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( tuple(), 'cp' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( tuple(), 'rsync' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('dump', ), 'map_file_to_obj' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('dump', ), 'files_on_volume' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('keep-on-site', ), 'add' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('keep-on-site', ), 'has' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
    ( ('keep-on-site', ), 'delete' ): {'expect_exit': 2, 'expect_exception': SystemExit()},
}

CMD_ARGS = {
    'get': 'getthis',
    'has': 'hasthis',
    'delete': 'deletethis',
    'set': 'setthis',
    'cp': '-a testfile1 cptargetfile',
    'rm': '-rf testfile1',
    'rsync': '-a --delete testfile1 testdir2',
    'map_file_to_obj': 'bucketname',
    'files_on_volume': 'volumename',
}
CMD_MANUAL_ARGS = {
    # Note, requires the 'subcommand' to be in CMD_ARGS or test will not be run
    # Requires a 'valid' site name, use dry run hard coded list
    ( ('keep-on-site', ), 'add' ): "dry_run_test_site1",
    ( ('keep-on-site', ), 'delete' ): "dry_run_test_site2",
}

def _check_subcommand_add_args(parentcmds, subcmd):
    parent_cmds_names = [cmd.name for cmd in parentcmds]
    key = (tuple(parent_cmds_names), subcmd.name)
    if key in CMD_MANUAL_ARGS:
        subcmd_args = CMD_MANUAL_ARGS[key]
    else:
        if subcmd.name not in CMD_ARGS:
            raise RuntimeError('Add command %s to CMD_ARGS' % subcmd.name)
        subcmd_args = CMD_ARGS[subcmd.name]
    _simple('-nvd ' + ' '.join(parent_cmds_names) + ' ' + subcmd.name + ' ' + subcmd_args)

def _check_subcommand_bare(parentcmds, subcmd):
    kwargs = {}
    subcmd_args = None
    parent_cmds_names = [cmd.name for cmd in parentcmds]
    key = (tuple(parent_cmds_names), subcmd.name)
    if key in BARE_COMMANDS_KNOWN_TO_FAIL:
        kwargs = BARE_COMMANDS_KNOWN_TO_FAIL[key]
        log.debug('updating KWARGS to %s', str(kwargs))
    _simple('-nvd ' + ' '.join(parent_cmds_names) + ' ' + subcmd.name, **kwargs)

def _check_all_subcommand_groups(parentcmds, clickcmd):
    parentcmds = list(parentcmds) # make a copy
    if clickcmd.name != 'cli':
        parentcmds.append(clickcmd)
    for subname, subcmd in clickcmd.commands.items():
        if isinstance(subcmd, click.Group):
            _simple('-nvd ' + ' '.join([cmd.name for cmd in parentcmds]) + ' ' + subname)
            _check_all_subcommand_groups(parentcmds, subcmd)
        else:
            #log.warning('skipped non-group subcommand %s of command %s', subname, hscli.cli.name)
            _check_subcommand_bare(parentcmds, subcmd)
            if subcmd.name in CMD_ARGS:
                _check_subcommand_add_args(parentcmds, subcmd)

def test_nvd_tld_subcommands():
    _check_all_subcommand_groups([], hscli.cli)

def test_nvd_eval_manual():
    _simple('-nvd eval -e THIS')
    _simple('-nvd eval -e THIS .')
    _simple('-nvd eval -e THIS --recursive')
    _simple('-nvd eval -e THIS --compact')
    _simple('-nvd eval -e THIS --nonfiles')
    _simple('-nvd eval -e THIS --raw')
    _simple('-nvd eval -e THIS --json')

def test_nvd_keyword_manual():
    _simple('-nvd keyword add MOUSE')
    _simple('-nvd keyword add MOUSE testfile1')
    _simple('-nvd keyword has MOUSE')
    _simple('-nvd keyword has MOUSE testfile1')
    _simple('-nvd keyword delete MOUSE')
    _simple('-nvd keyword delete MOUSE testfile1')
    _simple('-nvd keyword list')
    _simple('-nvd keyword list testfile1')

def find_hs_bin():
    cmd = os.path.dirname(sys.executable)
    cmd = os.path.join(cmd, 'hs')
    if os.path.exists(cmd):
        return cmd

    for path in os.environ["PATH"].split(os.pathsep):
        hs = os.path.join(path, 'hs')
        if os.path.exists(hs):
            return hs

    if os.path.exists('./hs'):
        return './hs'

    return "hs"

def test_nvd_eval_pipe_output():
    hs = find_hs_bin()
    if not os.path.exists(hs):
        log.warning('skipping stdout / stderr pipe testing as the hs command cannot be found')
        return
    res = sp.check_call((hs + ' -nvd eval -e 1 testfile1').split(), stdout=sp.PIPE)
    res = sp.check_call((hs + ' -nvd eval -e 1 testfile1').split(), stderr=sp.PIPE)
    res = sp.check_call((hs + ' -nvd eval -e 1 testfile1').split(), stdout=sp.PIPE, stderr=sp.PIPE)
