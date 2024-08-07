#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright 2021 Hammerspace
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import subprocess as sp
import sys
import os
import json
import pprint
import random
import io
import pathlib
import click
import platform
import hstk.hsscript as hss

# Windows compatability stuff
if platform.system().startswith('Windows') or platform.system().startswith('CYGWIN'):
    WINDOWS = True
    WIN_PADDING = b'\0'*50
else:
    WINDOWS = False
    WIN_PADDING = b''


# Helper object for containing global settings to be passed with context
class HSGlobals(object):
    def __init__(self, verbose=False, dry_run=False, debug=False, output_json=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.debug = debug
        if debug and not verbose:
            verbose = debug
        self.output_json = output_json



class OrderedGroup(click.Group):
    """
    Keep the order items are added in for --help output
    """

    def __init__(self, commands=None, name=None, **kwargs):
        self._ordered_commands = []
        self._cmd_aliases = {}
        if commands is not None:
            for cmd in commands:
                self._ordered_commands.append(cmd.name)
        super(OrderedGroup, self).__init__(name=name, commands=commands, **kwargs)

    def list_commands(self, ctx):
        return self._ordered_commands

    def add_command(self, cmd, name=None, aliases=[]):
        if name is not None:
            cmd_name = name
        else:
            cmd_name = cmd.name
        for alias in aliases:
            if alias in self._cmd_aliases:
                raise click.NoSuchOption(f'Duplicate alias ({alias}) added to group\n' +
                         '    New cmd: {cmd_name}\n' +
                         '    Orig cmd: {self._cmd_aliases[alias]}\n')
            self._cmd_aliases[alias] = cmd_name
        self._ordered_commands.append(cmd_name)
        super(OrderedGroup, self).add_command(cmd, name=None)

    def add_alias(self, cmd_name, *aliases):
        for alias in aliases:
            if alias in self._cmd_aliases:
                raise click.NoSuchOption(f'Duplicate alias ({alias}) added to group\n' +
                         '    New cmd: {cmd_name}\n' +
                         '    Orig cmd: {self._cmd_aliases[alias]}\n')
            self._cmd_aliases[alias] = cmd_name

    def get_command(self, ctx, cmd_name):
        """
        Command name resolution priority
        1: exact command name
        2: exact provided command alias
        3: try match a command (not alias) short version
        """
        if cmd_name in self._ordered_commands:
            pass
        elif cmd_name in self._cmd_aliases:
            cmd_name = self._cmd_aliases[cmd_name]
        else:
            matches = [x for x in self.list_commands(ctx)
                                if x.startswith(cmd_name)]
            if not matches:
                return None
            if len(matches) != 1:
                ctx.fail('%s matched too many commands: %s' % (cmd_name, ', '.join(sorted(matches))))
            cmd_name = matches[0]

        return super(OrderedGroup, self).get_command(ctx, cmd_name)

    def print_cmd_tree(self, cmd=None, indent=0):
        if cmd is None:
            cmd = self
        for sub in cmd._ordered_commands:
            if sub == "foo": # no idea...
                continue
            subcmd = cmd.commands[sub]
            print("%s %- 18s %s" % ("  "*indent, sub, subcmd.help))
            if isinstance(subcmd, OrderedGroup):
                self.print_cmd_tree(cmd=cmd.commands[sub], indent=indent+1)


#
# Top level group for subcommands
#
@click.group(cls=OrderedGroup, invoke_without_command=True, help="Hammerspace hammerscript cli")
@click.option('-v', '--verbose', count=True, help="Debug output")
@click.option('-n', '--dry-run', is_flag=True, help="Don't operate on files")
@click.option('-d', '--debug', is_flag=True, help="Show debug output")
@click.option('-j', '--json', 'output_json', is_flag=True, help="Use JSON formatted output")
@click.option('--cmd-tree', is_flag=True, help="Show help for available commands")
@click.pass_context
def cli(ctx, verbose, dry_run, debug, output_json, cmd_tree):
    """
    Top level function to kick of click parsing.
    verbose and dry-run are to be respected globally
    """
    if cmd_tree:
        print_full_cmd_tree()
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        print(ctx.command.get_help(ctx))
        sys.exit(0)

    ctx.obj = HSGlobals(verbose=verbose, dry_run=dry_run, debug=debug, output_json=output_json)
    if ctx.obj.verbose > 1:
        print ('V: verbose: ' + str(verbose))
        print ('V: dry_run: ' + str(dry_run))
        print ('V: debug: ' + str(debug))
        print ('V: output_json: ' + str(output_json))

def print_full_cmd_tree():
    """ Helper to allow cli function to call methods of itself """
    cli.print_cmd_tree()

def group_decorator(*decs):
    """
    Combine multiple @decorators into one usable @group decorator.  Return the outermost wrapper
    """
    def deco_group_apply(f):
        for dec in reversed(decs):
            f = dec(f)
        return f
    return deco_group_apply

class ShadCmd(object):
    @click.pass_context
    def __init__(ctx, self, shadgen, kwargs):
        self.ctx = ctx
        self.verbose = self.ctx.obj.verbose
        self.dry_run = self.ctx.obj.dry_run
        self.debug = self.ctx.obj.debug
        if 'force_json' in kwargs and kwargs['force_json']:
            self.output_json = True
        else:
            self.output_json = self.ctx.obj.output_json
        if 'outstream' in kwargs:
            self.outstream = kwargs['outstream']
        else:
            self.outstream = sys.stdout
        self.output_returns_error = False
        self.exit_status = 0

        self._paths = None
        self.shadgen = shadgen
        self.kwargs = kwargs
        self.process_kwargs()


    def process_kwargs(self):
        for argset in ( ('local', 'inherited', 'object', 'active', 'effective', 'share'), ('raw', 'compact'), ('exp_file', 'exp_stdin', 'exp'), ):
            cnt = 0
            for arg in argset:
                if self.checkopt(arg, self.kwargs):
                    cnt += 1
            if cnt > 1:
                self.ctx.fail("specify only one of the following options, found %d: %s" % (cnt, argset))

        if self.output_json:
            self.kwargs['json'] = True
        else:
            self.kwargs['json'] = False

        exp = None
        if self.checkopt('exp_file', self.kwargs):
            fn = self.kwargs['exp_file']
            fn = click.format_filename(fn)
            with open(fn) as fd:
                exp = fd.readline()
                if exp[-1] == '\n':
                    exp = exp[:-1]
                #exp = ''.join(exp) XXX what is this here for
                # XXX DFQ do we need to weed out newlines or anything?  Stripping a \n if it exists otherwise it gets passed into the shadow file name, otherwise just dumping the raw file as is (with the / replace)
        elif self.checkopt('exp_stdin', self.kwargs):
            exp = click.prompt('')
        elif self.checkopt('exp', self.kwargs):
            exp = self.kwargs['exp']
        if exp is not None:
            self.kwargs['value'] = hss.HSExp(exp)

        if self.checkopt('string', self.kwargs) and self.checkopt('value', self.kwargs):
            self.kwargs['value'].string = True

        if self.checkopt('input_json', self.kwargs) and self.checkopt('value', self.kwargs):
            self.kwargs['value'].input_json = True

        self.add_paths(*self.kwargs['pathnames'])

    def run_cmd(self, fname):
        """
        Create the .fs_command_gateway file for the exp_file argument and write the command
        then read from the .fs_command_gateway file
        """
        ret = []

        work_id = hex(random.randint(0,99999999))
        if fname.is_dir():
            gw = fname
            cmd = b'./'
        else:
            gw = fname.parent
            cmd = b'./' + fname.name.encode()
        gw = gw / f'.fs_command_gateway {work_id}'

        # First open, send the command
        vnprint(f'open( {gw} )')
        if self.dry_run:
            fd = io.StringIO()
        else:
            fd = gw.open('wb')

        try:
            cmd += self.shadgen(**self.kwargs).encode()
        except ValueError as e:
            if (        ('value' not in self.kwargs)
                    or  ('value' in self.kwargs and (not self.kwargs['value'])) ):
                sys.stderr.write('No expression (-e) provided')
                sys.exit(2)
            else:
                raise e

        # Add padding for windows, writes don't get pushed through the stack for if there is not enough data
        cmd += WIN_PADDING

        vnprint(f'write( {cmd} )')
        fd.write(cmd)

        # The flush here is only to make debugging easier so sync doesn't happen on close
        vnprint(f'flush()')
        fd.flush()

        vnprint(f'close( {gw} )')
        fd.close()

        # open again to collect the results
        vnprint(f'open( {gw} )')
        if self.dry_run:
            fd = io.StringIO('dry run output')
        else:
            fd = gw.open('r')
        vnprint('calling read()')
        ret = fd.readlines()
        vnprint(f'read() returned {len(ret)} lines {len("".join(ret))} bytes')

        vnprint(f'close( {gw} )')
        fd.close()

        return ret

    def runshad(self):
        ret = {}

        # Kick off the shadow commands one at a time, fix to run in parallel XXX
        for path in self.paths:
            ret[path] = []
            lines = self.run_cmd(path)
            ret[path].extend(lines)
        return ret

    def run(self):
        ret = self.runshad()
        if self.outstream is not None:

            print_filenames = False
            if len(ret.keys()) > 1:
                print_filenames = True

            for k, v in ret.items():
                if print_filenames:
                    self.outstream.write(f'##### {k}\n')
                for line in v:
                    self.outstream.write(line)
            self.outstream.flush()
        if self.output_returns_error:
            for k, v in ret.items():
                if len(v) > 0:
                    self.exit_status = 1
        return ret

    @property
    def paths(self):
        return self._paths

    @paths.setter
    def paths(self, paths):
        if paths is None:
            self._paths = None
            return True
        raise RuntimeError('Use add_paths()')

    def add_paths(self, *paths):
        if self._paths is None:
            self._paths = []
        for path in paths:
            self._paths.append(pathlib.Path(path))

    def checkopt(self, opt, optsdict):
        if opt in optsdict and optsdict[opt] not in (None, False):
            return True
        return False

def _param_defaults__pathnames_set_default(func):
    """
    Take the *paths and path parameters and convert to 'pathnames' list
    Also set the default to a single path of '.' if nothing was specified
    """
    def wrapper(*args, **kwargs):
        if 'path' in kwargs:
            kwargs['pathnames'] = [ kwargs['path'] ]
        if kwargs['pathnames'] is None or len(kwargs['pathnames']) == 0:
            vnprint('Setting default pathname to .')
            kwargs['pathnames'] = [ '.' ]
        func(*args, **kwargs)
    return wrapper

param_defaults = group_decorator(
            click.pass_context,
            click.argument('pathnames', metavar='paths', nargs=-1, type=click.Path(exists=True, readable=False)),
            _param_defaults__pathnames_set_default
        )

param_path = group_decorator(
    click.argument('path', nargs=1, type=click.Path(exists=True, readable=False), required=True, default="."),
    _param_defaults__pathnames_set_default
)
param_paths = group_decorator(
    click.argument('pathnames', metavar='paths', nargs=-1, type=click.Path(exists=True, readable=False)),
    _param_defaults__pathnames_set_default
)
param_dirpaths = group_decorator(
    click.argument('pathnames', metavar='dirpaths', nargs=-1, type=click.Path(exists=True, file_okay=False, readable=False)),
    _param_defaults__pathnames_set_default
)
param_sharepaths = group_decorator(
    click.argument('pathnames', metavar='sharepaths', nargs=-1, type=click.Path(exists=True, file_okay=False, readable=False)),
    _param_defaults__pathnames_set_default
)

param_recursive = click.option('-r', '--recursive', is_flag=True, help="Apply recursively")
param_nonfiles = click.option('--nonfiles', is_flag=True, help="Apply recursively to non files")
param_force = click.option('--force', is_flag=True, help="Force delete (suppress not found errors)")

param_eval = group_decorator(
            param_recursive,
            param_nonfiles,
            click.option('--raw', is_flag=True, help="Print raw output"),
            click.option('--compact', is_flag=True, help="Print compact output"),
        )

param_sum = group_decorator(
            click.option('--raw', is_flag=True, help="Print raw output"),
            click.option('--compact', is_flag=True, help="Print compact output"),
            click.option('--nonfiles', is_flag=True, help="Apply recursively to non files"),
        )

param_read = group_decorator(
            click.option('-l', '--local', is_flag=True, help="Show only settings directly applied to this file"),
            click.option('-h', '--inherited', is_flag=True, help="Show only settings inherited by this file from a parent"),
            click.option('-o', '--object', is_flag=True, help="Show only settings inherited by this file from the data object")
        )

param_objective_read = group_decorator(
            click.option('-l', '--local', is_flag=True, help="Show only settings directly applied to this file"),
            click.option('-h', '--inherited', is_flag=True, help="Show only settings inherited by this file from a parent"),
            click.option('-a', '--active', is_flag=True, help="Show the active objectives"),
            click.option('--effective', is_flag=True, help="Show the effective objectives"),
            click.option('--share', is_flag=True, help="Show the objectives from parent share")
        )

param_name = group_decorator(
            click.argument('name', nargs=1, required=True),
        )

param_value = group_decorator(
            click.option('-j', '--json', 'input_json', is_flag=True, help="Use JSON formatted input"),
            click.option('-i', '--exp-stdin', is_flag=True, help="Read expression from stdin"),
            click.option('-e', '--exp', nargs=1, help="Read expression passed as parameter"),
            click.option('-s', '--string', is_flag=True, help="Treat expression as raw string value"),
        )

param_unbound = group_decorator(
            click.option('-u', '--unbound', is_flag=True, help="Delay binding of any expression, it will be evaluated fresh each time"),
        )

def _cmd_retcode(hscmd, **kwargs):
    """
    Run a hammerscript command and return the retcode to the calling process
    """
    cmd = ShadCmd(hscmd, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

#
# Subcommands with noun only
#
@cli.command(name='eval', help="Evaluate hsscript expressions on a file")
@click.option('--interactive', is_flag=True, help="Interactivly read expressions from terminal and apply live")
@param_eval
@param_value
@param_defaults
def do_eval(ctx, *args, **kwargs):
    if kwargs['interactive']:
        kwargs['exp_stdin'] = True
        while True:
            cmd = ShadCmd(hss.eval, kwargs)
            cmd.run()
    try:
        cmd = ShadCmd(hss.eval, kwargs)
    except ValueError:
        print(ctx.get_help())
        print('\n')
        raise click.UsageError('Must provide expression (-e, -i, --interactive) to eval command')
    cmd.run()
    sys.exit(cmd.exit_status)

def hs_eval(*args, **kwargs):
    # Run an eval command but return the results as a string rather than displaying
    kwargs['force_json'] = True
    orig_pathnames = kwargs['pathnames']

    ret = {}
    for path in orig_pathnames:
        kwargs['pathnames'] = [ path ]
        kwargs['outstream'] = io.StringIO()
        cmd = ShadCmd(hss.eval, kwargs)
        cmd.run()
        cmd.outstream.seek(0)
        ret[path] = [ x[:-1] for x in cmd.outstream.readlines() ]
    return ret


@cli.command(name='sum', help="Perform fast calculations on a set of files")
@param_sum
@param_value
@param_defaults
def do_sum(ctx, *args, **kwargs):
    try:
        cmd = ShadCmd(hss.sum, kwargs)
    except ValueError:
        print(ctx.get_help())
        print('\n')
        raise click.UsageError('Must provide expression (-e, -i, --interactive) to sum command')
    cmd.run()
    sys.exit(cmd.exit_status)

def hs_sum(*args, **kwargs):
    # Run an sum command but return the results as a string rather than displaying
    kwargs['force_json'] = True
    orig_pathnames = kwargs['pathnames']

    ret = {}
    for path in orig_pathnames:
        kwargs['pathnames'] = [ path ]
        kwargs['outstream'] = io.StringIO()
        cmd = ShadCmd(hss.sum, kwargs)
        cmd.run()
        cmd.outstream.seek(0)
        ret[path] = [ x[:-1] for x in cmd.outstream.readlines() ]
    return ret

#
# Subcommands with noun verb, metadata and objectives
#

attribute_short_help = "[sub] inode metadata: schema no, value yes"
attribute_help = """
attribute: Manage Hammerspace embedded attribute metadata

Attributes can be defined on the fly, no schema pre-creation required.
Attributes can also hold a value.  Most values are string type (-s) but may
also be a number or expression (-e)

  ex: hs attribute set -n color -s blue path/to/file
"""
@cli.group(help=attribute_help, short_help=attribute_short_help, cls=OrderedGroup)
def attribute():
    attribute_short_help + '\n\n' + attribute_help
    pass

keyword_short_help = "[sub] inode metadata: schema no, value no"
keyword_help = """
keyword: Manage Hammerspace embedded keyword metadata

Keyword is a flexable metadata type that is created on the fly.  A keyword can
not store a value.
"""
@cli.group(help=keyword_help, short_help=keyword_short_help, cls=OrderedGroup)
def keyword():
    keyword_short_help + '\n\n' + keyword_help
    pass

label_short_help = "[sub] inode metadata: schema hierarchical, value no"
label_help = """
label: Manage Hammerspace embedded label metadata

Before a label can be added, it must be added to the labels scema via the admin
interface using the label-* admin cli commands.  Labels are good for situations
where you want to enforce the same wording/spelling/capitilaization/etc as well
as if you want one label to imply a series of parents.
"""
@cli.group(help=label_help, short_help=label_short_help, cls=OrderedGroup)
def label():
    label_short_help + '\n\n' + label_help
    pass

tag_short_help = "[sub] inode metadata: schema no, value yes"
tag_help = """
tag: Manage Hammerspace embedded tag metadata

Tags do not follow a schema (they can be created on the fly) and do not have a
value that can be stored with the key.  There is no list of tag names that have
been applied to the files of a share, the only way to generate a list is to
check all files in the share, which can be done via Hammerscript expression.
"""
@cli.group(help=tag_help, short_help=tag_short_help, cls=OrderedGroup)
def tag():
    tag_short_help + '\n\n' + tag_help
    pass

rekognition_tag_short_help = "[sub] inode metadata: schema no, value yes"
rekognition_tag_help = """
rekognition_tag
sub commands are used to view metadata added to an object by AWS's
rekognition service.  Contact support for details on how to configure
rekognition.
"""
@cli.group(help=rekognition_tag_help, short_help=rekognition_tag_short_help, cls=OrderedGroup)
def rekognition_tag():
    rekognition_tag_short_help + '\n\n' + rekognition_tag_help
    pass

objective_short_help = "[sub] control file placement on backend storage"
@cli.group(short_help=objective_short_help, cls=OrderedGroup)
def objective():
    objective_help = objective_short_help + '\n\n' + """
    TODO XXX
    """
    pass



@attribute.command(name='list', help="list all attributes and values applied")
@param_eval
@param_read
@param_defaults
def do_attribute_list(ctx, *args, **kwargs):
    _cmd_retcode(hss.attribute_list, **kwargs)

@tag.command(name='list', help="list all tags and values applied")
@param_eval
@param_read
@param_defaults
@param_unbound
def do_tag_list(ctx, *args, **kwargs):
    _cmd_retcode(hss.tag_list, **kwargs)

@rekognition_tag.command(name='list', help="list all rekognition tags and values applied")
@param_eval
@param_read
@param_defaults
def do_rekognition_tag_list(ctx, *args, **kwargs):
    _cmd_retcode(hss.rekognition_tag_list, **kwargs)

@keyword.command(name='list', help="list all keywords applied")
@param_eval
@param_read
@param_defaults
def do_keyword_list(ctx, *args, **kwargs):
    _cmd_retcode(hss.keyword_list, **kwargs)

@label.command(name='list', help="list all labels applied")
@param_eval
@param_read
@param_defaults
def do_label_list(ctx, *args, **kwargs):
    _cmd_retcode(hss.label_list, **kwargs)

@objective.command(name='list', help="list all (objective,expression) pairs assigned")
@param_eval
@param_objective_read
@param_defaults
def do_objective_list(ctx, *args, **kwargs):
    _cmd_retcode(hss.objective_list, **kwargs)



@attribute.command(name='get', help="Get the attribute's value")
@param_eval
@param_read
@param_name
@param_unbound
@param_defaults
def do_attribute_get(ctx, *args, **kwargs):
    _cmd_retcode(hss.attribute_get, **kwargs)

@attribute.command(name='has', help="Is the inode's attribute value non-empty")
@param_eval
@param_read
@param_name
@param_defaults
def do_attribute_has(ctx, *args, **kwargs):
    _cmd_retcode(hss.attribute_get, **kwargs)

@tag.command(name='get', help="Get the tag's value")
@param_eval
@param_read
@param_name
@param_unbound
@param_defaults
def do_tag_get(ctx, *args, **kwargs):
    _cmd_retcode(hss.tag_get, **kwargs)

@rekognition_tag.command(name='get', help="Get the rekognition tag's value")
@param_eval
@param_read
@param_name
@param_unbound
@param_defaults
def do_rekognition_tag_get(ctx, *args, **kwargs):
    _cmd_retcode(hss.rekognition_tag_get, **kwargs)

@tag.command(name='has', help="Is the inode's tag value non-empty")
@param_eval
@param_read
@param_name
@param_defaults
def do_tag_has(ctx, *args, **kwargs):
    _cmd_retcode(hss.tag_has, **kwargs)

@rekognition_tag.command(name='has', help="Is the inode's rekognition tag value non-empty")
@param_eval
@param_read
@param_name
@param_defaults
def do_rekognition_tag_has(ctx, *args, **kwargs):
    _cmd_retcode(hss.rekognition_tag_has, **kwargs)

@keyword.command(name='has', help="Is the keyword assigned to the file")
@param_eval
@param_read
@param_name
@param_defaults
def do_keyword_has(ctx, *args, **kwargs):
    _cmd_retcode(hss.keyword_has, **kwargs)

@label.command(name='has', help="Is the label assigned to the file")
@param_eval
@param_read
@param_name
@param_defaults
def do_label_has(ctx, *args, **kwargs):
    _cmd_retcode(hss.label_has, **kwargs)

@objective.command(name='has', help="Get/list objective assignments")
@param_eval
@param_objective_read
@param_name
@param_value
@param_defaults
def do_objective_has(ctx, *args, **kwargs):
    _cmd_retcode(hss.objective_has, **kwargs)



@attribute.command(name='delete', help="remove attribute values from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_attribute_del(ctx, *args, **kwargs):
    _cmd_retcode(hss.attribute_del, **kwargs)

@tag.command(name='delete', help="remove tag values from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_tag_del(ctx, *args, **kwargs):
    _cmd_retcode(hss.tag_del, **kwargs)

@rekognition_tag.command(name='delete', help="remove rekognition tag values from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_rekognition_tag_del(ctx, *args, **kwargs):
    _cmd_retcode(hss.rekognition_tag_del, **kwargs)

@keyword.command(name='delete', help="remove keywords from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_keyword_del(ctx, *args, **kwargs):
    _cmd_retcode(hss.keyword_del, **kwargs)

@label.command(name='delete', help="remove labels from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_label_del(ctx, *args, **kwargs):
    _cmd_retcode(hss.label_del, **kwargs)

@objective.command(name='delete', help="remove (objective,expression) pair from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_value
@param_defaults
def do_objective_del(ctx, *args, **kwargs):
    _cmd_retcode(hss.objective_del, **kwargs)



@keyword.command(name='add', help="add a keyword to inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_defaults
def do_keyword_add(ctx, *args, **kwargs):
    _cmd_retcode(hss.keyword_add, **kwargs)

@label.command(name='add', help="add a label to inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_defaults
def do_label_add(ctx, *args, **kwargs):
    _cmd_retcode(hss.label_add, **kwargs)

@attribute.command(name='set', help="Add/Set value of attribute on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_attribute_set(ctx, *args, **kwargs):
    _cmd_retcode(hss.attribute_set, **kwargs)

@attribute.command(name='add', help="Add/Set value of attribute on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_attribute_add(ctx, *args, **kwargs):
    _cmd_retcode(hss.attribute_set, **kwargs)

@tag.command(name='set', help="Add/Set value of tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_tag_set(ctx, *args, **kwargs):
    _cmd_retcode(hss.tag_set, **kwargs)

@rekognition_tag.command(name='set', help="Add/Set value of rekognition tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_rekognition_tag_set(ctx, *args, **kwargs):
    _cmd_retcode(hss.rekognition_tag_set, **kwargs)

@tag.command(name='add', help="Add/Set value of tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_tag_add(ctx, *args, **kwargs):
    _cmd_retcode(hss.tag_set, **kwargs)

@rekognition_tag.command(name='add', help="Add/Set value of rekognition tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_rekognition_tag_add(ctx, *args, **kwargs):
    _cmd_retcode(hss.rekognition_tag_set, **kwargs)

@objective.command(name='add', help="Add (objective,expression) pair to inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_objective_set(ctx, *args, **kwargs):
    _cmd_retcode(hss.objective_add, **kwargs)


###
### Simple commands
###

@click.pass_context
def vnprint(ctx, line):
    """ Print a line if verbose or dry-run """
    if ctx.obj.verbose > 0 or ctx.obj.dry_run:
        tag = 'V: '
        if ctx.obj.dry_run:
            tag = 'N: '
        print(tag + line)

@cli.command(name='rm', help="Fast offloaded rm -rf")
@click.option('-r', '-R', '--recursive', is_flag=True, help="Required for fast mode, remove directories and their contents recursively")
@click.option('-f', '--force', is_flag=True, help="Required for fast mode, ignore nonexistent files and arguments")
@click.option('-i', is_flag=True, help="Disables fast mode, passed through to system rm")
@click.option('-I', 'I', is_flag=True, help="Disables fast mode, passed through to system rm")
@click.option('--interactive', default=None, help="Disables fast mode, passed through to system rm")
@click.option('--one-file-system', is_flag=True, help="Disables fast mode, passed through to system rm")
@click.option('--no-preserve-root', is_flag=True, help="Disables fast mode, passed through to system rm")
@click.option('--preserve-root', is_flag=True, help="Disables fast mode, passed through to system rm")
@click.option('-d', '--dir', is_flag=True, help="Disables fast mode, passed through to system rm")
@click.option('-v', '--verbose', is_flag=True, help="Disables fast mode, passed through to system rm")
@click.argument('pathnames', nargs=-1, type=click.Path(exists=True), required=True)
@click.pass_context
def do_rm_rf(ctx, *args, **kwargs):
    passthrough_opt_flags = [ 'i', 'I', 'one_file_system', 'no_preserve_root', 'dir', 'verbose' ]

    call_out_args = []
    for opt in passthrough_opt_flags:
        if kwargs[opt]:
            if len(opt) > 1:
                call_out_args.append('--' + opt.replace('_', '-'))
            else:
                call_out_args.append('-' + opt)

    # Custom handle non-flag passthrough options
    if opt == 'interactive':
        call_out_args.append('--' + opt)
        if kwargs[opt] is not None:
            call_out_args.append(kwargs[opt])

    if len(call_out_args) > 0 or not (kwargs['force'] and kwargs['recursive']):
        vnprint('Unsupported options supplied, falling back to system rm')
        call_out_args += kwargs['pathnames']
        call_out_args.insert(0, 'rm')
        vnprint('Calling: ' + ' '.join(call_out_args))
        if ctx.obj.dry_run:
            return True
        else:
            return sp.call(call_out_args)

    others = []
    dirs = []
    for fpath in kwargs['pathnames']:
        if os.path.isdir(fpath):
            dirs.append(fpath)
        elif os.path.exists(fpath):
            others.append(fpath)
        else:
            vnprint('Path not found, ignoring due to --force: %s' % (fpath))

    kwargs['pathnames'] = dirs
    cmd = ShadCmd(hss.rm_rf, kwargs)
    cmd.run()

    # unlink any non-dirs
    for fpath in others:
        vnprint('unlink( ' + fpath + ' )')
        if not ctx.obj.dry_run:
            os.unlink(fpath)

    # rmdir the base directories, the shadow command doesn't clean these up
    for fpath in dirs:
        vnprint('rmdir( ' + fpath + ' )')
        if not ctx.obj.dry_run:
            os.rmdir(fpath)
    sys.exit(cmd.exit_status)


def do_cp_a_fallback(ctx, kwargs, args, srcs, dest):
    args = copy.copy(args)
    if 'archive' in kwargs and kwargs['archive']:
        args.append('--archive')
    args.extend(srcs)
    args.append(dest)
    args.insert(0, 'cp')
    vnprint('Calling: ' + ' '.join(args))
    if ctx.obj.dry_run:
        return 0
    else:
        return sp.call(args)

def do_cp_a_fallback_handle_error(ctx, kwargs, args, srcs, dest, reason):
    vnprint(reason + ', falling back to system cp')
    res = do_cp_a_fallback(ctx, kwargs, args, srcs, dest)
    if res != 0:
        print('Error %d processing passthrough cp of path %s: %s' % (res, ' '.join(srcs), os.strerror(res)))
        print('Aborting')
        sys.exit(res)
    return 0


@cli.command(name='cp', help="Fast offloaded recursive copy via clone",
        context_settings=dict(ignore_unknown_options=True,))
@click.option('-a', '--archive', is_flag=True, help="Required for fast mode, CoW 'copy' a file or recursivly copy a directory by clone")
@click.argument('srcs', nargs=-1, required=True, type=click.UNPROCESSED) # shove any unknown arguments in here
@click.argument('dest', nargs=1, required=True)
@click.pass_context
def do_cp_a(ctx, *args, **kwargs):
    # Look for anything in src that is not a file/dir,
    # any unknown options will be shoved here due to click.UNPROCESSED above
    # if anything is found, trigger a fall back to system cp
    call_out_args = []
    tmp_list = list(kwargs['srcs'])
    for arg in tmp_list:
        if not os.path.exists(arg):
            call_out_args.append(arg)
    for arg in call_out_args:
        tmp_list.remove(arg)
    kwargs['srcs'] = tuple(tmp_list)

    fast_sources = []
    dest = kwargs['dest']
    srcs = kwargs['srcs']

    if len(call_out_args) > 0 or not kwargs['archive']:
        reason='Unsupported options or non-existant source supplied'
        return do_cp_a_fallback_handle_error(ctx, kwargs, call_out_args, srcs, dest, reason)

    # NOTE: Trailing /s have no effect on behavior in either single or multi source mode

    # Handle single source file nuances
    if os.path.exists(dest) and not os.path.isdir(dest):
        reason='Destination exists but is not a directory'
        return do_cp_a_fallback_handle_error(ctx, kwargs, call_out_args, srcs, dest, reason)

    is_single_arg = False
    if len(srcs) == 1:
        is_single_arg = True
        src = srcs[0]
        if not os.path.isdir(src):
            reason='Single source %s is not a directory, use cp --reflink for faster copy' % (src)
            return do_cp_a_fallback_handle_error(ctx, kwargs, call_out_args, srcs, dest, reason)
        source_entries = os.listdir(src)

        if not os.path.exists(dest):
            # If dest doesn't exist and src is a directory, cp makes dest and
            # copies only the contents of srcs in
            vnprint('mkdir '+dest)
            if not ctx.obj.dry_run:
                os.mkdir(dest)
            for entry in source_entries:
                fast_sources.append(os.path.join(src, entry))
        else:
            # We know from previous test that dest exists and is a directory
            # In this case, cp just copes the whole directory src as a child of
            # dest rather than the individual children
            fast_sources.append(src)

    # Now to multi source mode
    if not os.path.isdir(dest):
        # Use cp -a to generate the error message
        reason='Destination directory does not exist'
        return do_cp_a_fallback_handle_error(ctx, kwargs, call_out_args, srcs, dest, reason)

    dest_stat = os.stat(dest)

    # In multi source mode, each source is just copied into dest as a child of dest, always
    if not is_single_arg:
        for src in srcs:
            fast_sources.append(src)

    for src in fast_sources:
        # Pre-flight checks, fallback if any fail
        if not os.path.exists(src):
            # use cp -a to generate the error message
            reason='Source %s does not exist' % (src)
            return do_cp_a_fallback_handle_error(ctx, kwargs, call_out_args, srcs, dest, reason)

        src_stat = os.stat(src)
        if src_stat.st_dev != dest_stat.st_dev:
            reason='Source %s is on different filesystem from destination' % (src)
            return do_cp_a_fallback_handle_error(ctx, kwargs, call_out_args, srcs, dest, reason)

        # XXX Need to detect any filesystems mounted in the source tree

    # Rely on pdfs to detect colisions and error out?
    # XXX For this release, do extra sanity checks, won't be needed in the future
    for src in fast_sources:
        entry = os.path.basename(src)
        if len(entry) == 0:
            entry = src
        tgt = os.path.join(dest, entry)
        if os.path.exists(tgt):
            reason='Source item "%s" collides with existing item "%s" in destination' % (src, tgt)
            return do_cp_a_fallback_handle_error(ctx, kwargs, call_out_args, srcs, dest, reason)

    kwargs['dest_inode'] = dest_stat.st_ino
    kwargs['pathnames'] = fast_sources
    cmd = ShadCmd(hss.cp_a, kwargs)
    cmd.run()
    if cmd.exit_status != 0:
        print('Error %d processing offloaded cp -a of paths %s: %s' % (cmd.exit_status, ' '.join(fast_sources), os.strerror(cmd.exit_status)))
        print('Aborting')
        sys.exit(cmd.exit_status)

    # Walk the tree, following any assimilation to block returning till assims are complete
    hs_dirs_count(dest)

    sys.exit(0)



@click.pass_context
def _copy_md(ctx, src, dest):
    vnprint('stat '+src)
    if not ctx.obj.dry_run:
        src_st = os.stat(src)
        vnprint('chown %d.%d %s' % (src_st.st_uid, src_st.st_gid, dest))
        os.chown(dest, src_st.st_uid, src_st.st_gid)
        vnprint('chmod %o %s' % (src_st.st_mode, dest))
        os.chmod(dest, src_st.st_mode)
    else:
        vnprint('chown dry_run.dry_run %s' % (dest))
        vnprint('chmod dry_run %s' % (dest))

    # XXX Add copying of acls
    # XXX Add copying of HS metadata like tags, objectives, etc

@cli.command(name='rsync', help="Fast offloaded recursive directory equalizer (Add and Delete)",
        context_settings=dict(ignore_unknown_options=True,))
@click.option('-a', '--archive', is_flag=True, help="Required, must specify -a --delete")
@click.option('--delete', is_flag=True, help="Required, must specify -a --delete")
@click.argument('src', nargs=1, required=True,
        type=click.Path(exists=True, readable=True))
@click.argument('dest', nargs=1, required=True,
        type=click.Path(exists=False, writable=True))
@click.pass_context
def do_rsync_a_delete(ctx, src, dest, *args, **kwargs):
    if not kwargs['archive'] or not kwargs['delete']:
        reason="Must provide both --delete and --archive options, this is the only supported method for this tool, which may remove data at the destination path"
        raise click.UsageError(reason, ctx)

    # NOTE: Trailing /s are important in rsync mode, which is different from cp-a
    if os.path.isfile(src):
        src_is_file = True
    else:
        src_is_file = False

    if os.path.isdir(src):
        src_is_dir = True
    else:
        src_is_dir = False

    if src[-1] == os.sep:
        src_ends_slash = True
    else:
        src_ends_slash = False

    src_undelete = False

    if os.path.isdir(dest):
        dest_is_dir = True
    else:
        dest_is_dir = False

    if dest[-1] == os.sep:
        dest_ends_slash = True
    else:
        dest_ends_slash = False

    if os.path.exists(dest):
        dest_exists = True
    else:
        dest_exists = False

    dest = os.path.abspath(dest)

    if src_is_file:
        # Dest needs to be a directory and cannot contain a file with the src files name
        if (not src_ends_slash) and (not dest_ends_slash) \
                and (not src_is_dir) and (not dest_is_dir) \
                and os.path.basename(src) == os.path.basename(dest):
            # Assume should be file on both sides
            dest_fname = os.path.basename(dest)
            dest_parent = os.path.dirname(dest)
        elif (not dest_ends_slash) and (not dest_exists):
            # In this case, rsync would create a file, not a dir, don't support that
            # Snag a rename for future failure
            dest_fname = os.path.basename(dest)
            dest_parent = os.path.dirname(dest)
        elif dest_ends_slash or dest_is_dir or (not dest_exists):
            # should be directory or already is directory
            dest_fname = os.path.basename(src)
            dest_parent = dest
        else:
            # assume it is a file that was specified
            dest_fname = os.path.basename(dest)
            dest_parent = os.path.dirname(dest)
        src_fname = os.path.basename(src)
        src_parent = os.path.dirname(src)

        if (dest_fname != src_fname):
            if src_fname.startswith(dest_fname + '[#D'):
                # allow restoring from undelete filename, which does have different name from dest
                src_undelete = True
            else:
                reason="This rsync like tool can not handle renaming a file as part of the copy\n" + \
                    "please provide a source filename and a target directory/ (include trailing /)\n" + \
                    "src filename: %s     dest filename: %s" % (os.path.basename(src), dest_fname)
                raise click.UsageError(reason, ctx)

        elif not os.path.exists(dest_parent):
            vnprint('mkdir '+dest_parent)
            if not ctx.obj.dry_run:
                os.mkdir(dest_parent)
            _copy_md(src_parent, dest_parent)

        elif (not ctx.obj.dry_run) and (not os.path.isdir(dest_parent)):
            reason="Source %s is a file but unable to find the destination/parent directory %s" % (src, dest_parent)
            raise click.UsageError(reason, ctx)

        dest_tgt = dest_parent

    elif src_is_dir:
        # in the following / patterns, must create srcdir name and use as target
        if ((not src_ends_slash) and (not dest_ends_slash)) or \
                ((not src_ends_slash) and dest_ends_slash):
            dest_parent = os.path.join(dest, os.path.basename(src))
            dest_fname = None
            dest_tgt = dest_parent
            if not os.path.exists(dest):
                vnprint('mkdir '+dest)
                if not ctx.obj.dry_run:
                    os.mkdir(dest)
        else:
            dest_parent = dest
            dest_fname = None
            dest_tgt = dest
        src_fname = None
        src_parent = src

        src_dname = os.path.basename(src)
        dest_dname = os.path.basename(dest)
        if src_dname.startswith(dest_dname + '[#D'):
            src_undelete = True

        if not os.path.exists(dest_tgt):
            vnprint('mkdir '+dest_tgt)
            if not ctx.obj.dry_run:
                os.mkdir(dest_tgt)
            dest_is_dir = True
        if (not ctx.obj.dry_run) and (not dest_is_dir):
            reason="Source %s is a directory but dest %s is not" % (src, dest)
            raise click.UsageError(reason, ctx)
    else:
        reason="Source %s is not a file or directory" % (src)
        raise click.UsageError(reason, ctx)

    vnprint('stat src '+src)
    src_stat = os.stat(src)
    vnprint('src inode %d' % (src_stat.st_ino))
    vnprint('stat dest_tgt '+dest_tgt)
    dest_tgt_stat = os.stat(dest_tgt)
    vnprint('dest_tgt inode %d' % (dest_tgt_stat.st_ino))

    if src_stat.st_dev != dest_tgt_stat.st_dev:
        reason='Source (stat_dev %d) is on different filesystem from destination (stat_dev %d)' % (src_stat.st_dev, dest_tgt_stat.st_dev)
        raise click.UsageError(reason, ctx)
    # XXX detect any filesystems mounted in the source tree?

    # Detect any requests inside .snapshot/current/ that are not undelete files.
    if dest_exists:
        dest_stat = os.stat(dest)
        if src_stat.st_ino == dest_stat.st_ino:
            versions = hs_eval(exp='VERSION', pathnames=[src, dest])
            try:
                versions[src] = int(versions[src][0])
                versions[dest] = int(versions[dest][0])
            except Exception as e:
                print('Error parsing response from VERSION, response was:')
                pprint.pprint(versions)
                sys.stdout.flush()
                raise e
            if versions[src] == 2 and (not src_undelete):
                vnprint("Trying to restore from .snapshot/current source and dest are the same file, doing nothing")
                sys.exit(0)
            elif versions[dest] > 1:
                reason="Dest %s has version %d is in .snapshot/, can not restore TO a snapshot, only FROM" % (dest, versions[dest])
                raise click.UsageError(reason, ctx)

    kwargs['dest_inode'] = dest_tgt_stat.st_ino
    kwargs['pathnames'] = [ src ]
    cmd = ShadCmd(hss.cp_a, kwargs)
    cmd.run()
    if cmd.exit_status != 0:
        print('Error %d processing offloaded rsync of paths %s: %s' % (cmd.exit_status, src, os.strerror(cmd.exit_status)))
        print('Aborting')
        sys.exit(cmd.exit_status)

    # Walk the tree, following the assimilation to block returning till assim is complete
    hs_dirs_count(dest_tgt)

    if not src_is_file:
        # Manually always copy the metadata for all directory sources
        _copy_md(src_parent, dest_parent)
    sys.exit(0)


@cli.command(name='collsum', help="Usage details about one/all collections in whole share (fast)")
@click.argument('collection', nargs=1, required=True, default="all")
@click.option('--collation', nargs=1, required=False)
@param_sharepaths
@click.pass_context
def do_collection_sum(ctx, collection, collation, *args, **kwargs):
    if collation is None:
        eval_args = {
                'exp': 'collection_sums("%s")' % (collection),
            }
    else:
        eval_args = {
                'exp': 'collection_sums("%s")[SUMMATION("%s")]' % (collection, collation),
            }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)



#
# Status reports
#
@click.group(help="[sub] System, component, task status", cls=OrderedGroup)
def status():
    pass
cli.add_command(status)

@status.command(name='assimilation', help="State of current assimilations")
@param_sharepaths
@click.pass_context
def do_assim_status(ctx, *args, **kwargs):
    eval_args = {
            'exp': 'assimilation_details',
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@status.command(name='csi', help="Details about the kubernetes CSI")
@param_sharepaths
@click.pass_context
def do_csi_status(ctx, *args, **kwargs):
    eval_args = {
            'exp': 'attributes.csi_details',
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@status.command(name='collections', help="Collections present in the share")
@param_sharepaths
@click.pass_context
def do_collections_list(ctx, *args, **kwargs):
    eval_args = {
            'exp': 'collections',
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@status.command(name='errors', help="Files in the share with errors")
@click.option('--dump', is_flag=True, help="Dump inode details, only on files in dir+dirpath")
@param_sharepaths
@click.pass_context
def do_errored_files(ctx, dump, *args, **kwargs):
    if dump:
        sum_args = {
                'exp': '(IS_FILE AND ERRORS)?SUMS_TABLE{|KEY=ERRORS,|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
            }
        kwargs.update(sum_args)
    else:
        eval_args = {
                'exp': 'IS_FILE and errors!=0?dump_inode',
                'recursive': True,
            }
        kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@status.command(name='open', help="Files open each dir(s)")
@param_dirpaths
@click.pass_context
def do_show_open_files(ctx, *args, **kwargs):
    sum_args = {
            'exp': '(IS_FILE AND IS_OPEN)?{1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@status.command(name='replication', help="Replication progress for the share(s)")
@param_sharepaths
@click.pass_context
def do_replication_status(ctx, *args, **kwargs):
    eval_args = {
            'exp': 'replication_details',
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@status.command(name='sweeper', help="Progress of sweeper (checks file placement) for each share(s)")
@param_sharepaths
@click.pass_context
def do_sweeper_status(ctx, *args, **kwargs):
    eval_args = {
            'exp': 'sweep_details',
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@status.command(name='volume', help="Health of volumes backing the share(s)")
@param_sharepaths
@click.pass_context
def do_volume_health(ctx, *args, **kwargs):
    eval_args = {
            'exp': '{|::#A=storage_volumes.name[row],|::#B=storage_volumes.volume_status[row],|::#C=storage_volumes.oper_status[row]}[rows(storage_volumes)]',
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)



#
# Capacity and inode usage
#
@click.group(name='usage', short_help="[sub] Resource utilization such as capacity or inode", cls=OrderedGroup)
def usage():
    pass
cli.add_command(usage)

@usage.command(name='alignment', help="Alignment state of files each file(s) of files in dir(s)")
@click.option('--top-files', is_flag=True, help="include largest files in each alignment state")
@param_paths
@click.pass_context
def do_file_alignment(ctx, top_files, *args, **kwargs):
    if top_files:
        sum_args = {
                'exp': 'IS_FILE?SUMS_TABLE{|KEY=OVERALL_ALIGNMENT,|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
            }
    else:
        sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY=OVERALL_ALIGNMENT,|VALUE=1}',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='virus-scan', help="Virus scan state of files each file(s) of files in dir(s)")
@click.option('--top-files', is_flag=True, help="include largest files in each virus scan state")
@param_paths
@click.pass_context
def do_file_virus_scan(ctx, top_files, *args, **kwargs):
    if top_files:
        sum_args = {
                'exp': 'IS_FILE?SUMS_TABLE{|KEY=ATTRIBUTES.VIRUS_SCAN,|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
            }
    else:
        sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY=ATTRIBUTES.VIRUS_SCAN,|VALUE=1}',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='owner', help="Owner state of files each file(s) of files in dir(s)")
@click.option('--top-files', is_flag=True, help="include largest files of each owner")
@param_paths
@click.pass_context
def do_usage_owner(ctx, top_files, *args, **kwargs):
    if top_files:
        sum_args = {
                'exp': 'IS_FILE?SUMS_TABLE{|KEY=OWNER,|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
            }
    else:
        sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY=OWNER,|VALUE=1}',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='online', help="Summary of files on NAS volumes in the dir")
@param_dirpaths
@click.pass_context
def do_online_files(ctx, *args, **kwargs):
    sum_args = {
            'exp': 'IS_ONLINE?{1FILE,SPACE_USED,TOP10_TABLE{{space_used,DPATH}}}',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='volume', help="Usage for each volume backing each dir(s)")
@click.option('--top-files', is_flag=True, help="Show largest files on each volume")
@click.option('--deep', is_flag=True, help="Might take a long time, XXX")
@param_paths
@click.pass_context
def do_volume_usage(ctx, top_files, deep, *args, **kwargs):
    sum_args = {
            'exp': 'IS_FILE?ROWS(INSTANCES)?SUMS_TABLE{|::KEY=INSTANCES[ROW].VOLUME,|::VALUE=1}[ROWS(INSTANCES)]:SUMS_TABLE{|KEY=#EMPTY,|::VALUE=1}',
        }
    kwargs.update(sum_args)
    if top_files:
        kwargs['exp'] = 'IS_FILE?ROWS(INSTANCES)?SUMS_TABLE{|::KEY=INSTANCES[ROW].VOLUME,|::VALUE={1FILE,INSTANCES[ROW].SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}[ROWS(INSTANCES)]:SUMS_TABLE{|KEY=#EMPTY,|::VALUE={1FILE, SPACE_USED, TOP10_TABLE{{space_used,dpath}}}}'
    if deep:
        kwargs['exp'] = 'IS_FILE?ROWS(INSTANCES)?SUMS_TABLE{|::KEY=INSTANCES[ROW].VOLUME,|::VALUE={1FILE,INSTANCES[ROW].SPACE_USED,TOP100_TABLE{{space_used,dpath}}}}[ROWS(INSTANCES)]:SUMS_TABLE{|KEY=#EMPTY,|::VALUE={1FILE, SPACE_USED, TOP100_TABLE{{space_used,dpath}}}}'
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='user', help="Users consuming the most capacity in each dir(s)")
@click.option('--details', is_flag=True, help="Include details like largest files per user")
@param_dirpaths
@click.pass_context
def do_users_top_usage(ctx, details, *args, **kwargs):
    sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY={OWNER,OWNER_GROUP},|VALUE=SPACE_USED}',
        }
    if details:
        sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY={OWNER,OWNER_GROUP},|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='objectives', help="Objectives applied and capacity managed by dir(s)")
@param_dirpaths
@click.pass_context
def do_objectives_usage(ctx, *args, **kwargs):
    sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|::KEY=LIST_OBJECTIVES_ACTIVE[ROW],|::VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}[ROWS(LIST_OBJECTIVES_ACTIVE)]',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='mime_tags', help="All tags added by mime discovery on dir(s)")
@param_dirpaths
@click.pass_context
def do_list_mime_tags(ctx, *args, **kwargs):
    sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{attributes.mime.string,{1FILE,SPACE_USED,TOP10_TABLE{{SPACE_USED,DPATH}}}}',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='rekognition_tags', help="All tags added by Rekognition on dir(s)")
@param_dirpaths
@click.pass_context
def do_list_rekognition_tags(ctx, **kwargs):
    sum_args = {
            'exp': 'IS_FILE?ISTABLE(LIST_REKOGNITION_TAGS)?SUMS_TABLE{|::KEY=LIST_REKOGNITION_TAGS()[ROW].NAME,|::VALUE={1FILE,TOP10_TABLE{{LIST_REKOGNITION_TAGS()[ROW].value,dpath}}}}[ROWS(LIST_REKOGNITION_TAGS())]',
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

@usage.command(name='dirs', help="Number of subdirectories under specified directory(ies), not including that directory")
@param_dirpaths
@click.pass_context
def do_dirs_count(ctx, *args, **kwargs):
    # Also, an efficient way to follow an assimilation, this will block until it completes
    sum_args = {
            'exp': '1',
            'nonfiles': True,
        }
    kwargs.update(sum_args)
    _cmd_retcode(hss.sum, **kwargs)

def hs_dirs_count(*paths, **kwargs):
    """Call with one or more directory paths, get the results as JSON"""
    sum_args = {
            'exp': '1',
            'nonfiles': True,
            'pathnames': paths,
        }
    kwargs.update(sum_args)
    return hs_sum(**kwargs)



#
# performance and event counters
#
@click.group(name='perf', help="[sub] Performance and operation stats", cls=OrderedGroup)
def perf_grp():
    pass
cli.add_command(perf_grp)

@click.pass_context
def _dot_stats_files_paths(ctx, paths):
    """
    This file is used to store the saved off/old stats (counter values) as a tag 'old_stats'
    """
    statsfs = {}

    for path in paths:
        # eval -e path to find the root of the share, create .stats there?
        statsf = os.path.join(path, '.stats')

        if ctx.obj.dry_run:
            vnprint('dry run, not creating .stats file ' + statsf)
        elif not os.path.exists(statsf):
            vnprint('creating .stats file ' + statsf)
            with open(statsf, 'w') as fd:
                pass
        statsfs[path] = statsf

    return statsfs

@perf_grp.command(name='clear', help="Clear op/perf counters on share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_clear(ctx, *args, **kwargs):
    """
    Doesn't actually 'clear' the stats, just saves off the current counters to a tag 'old_stats' that is then
    diffed from the latest stats on future reads.  If needed, creates a .stats file to store this tag
    """
    # manual method of clearing stats via pdfs
    # echo hi > $share/?.attribute=pdfs_stats
    statsfs = _dot_stats_files_paths(kwargs['pathnames'])
    tag_args = {
            'exp': 'fs_stats.op_stats',
            'name': 'old_stats',
            'pathnames': statsfs,
        }
    kwargs.update(tag_args)
    _cmd_retcode(hss.tag_set, **kwargs)

@perf_grp.command(name='top_calls', help="Show filesystem calls consuming the most time on share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_top_calls(ctx, *args, **kwargs):
    statsfs = _dot_stats_files_paths(kwargs['pathnames'])
    eval_args = {
            'exp': '{(fs_stats.op_stats-get_tag("old_stats")),TOP100_TABLE{|::KEY={#A[PARENT.ROW].op_count,#A[PARENT.ROW].name,#A[PARENT.ROW].op_count,#A[PARENT.ROW].op_time,#A[PARENT.ROW].op_avg}}[ROWS(#A)]}.#B',
            'pathnames': statsfs,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@perf_grp.command(name='top_funcs', help="Top time consuming functions on share(s)")
@click.option('--op', nargs=1, default='all', help="Restrict to reporting to funcs in a specific op")
@param_sharepaths
@click.pass_context
def do_report_stats_funcs(ctx, op, *args, **kwargs):
    statsfs = _dot_stats_files_paths(kwargs['pathnames'])
    eval_args = {
            'exp': '{(FS_STATS.OP_STATS-get_tag("old_stats"))[|NAME="%s"].func_stats,TOP100_TABLE{|::KEY={#A[PARENT.ROW].op_time,#A[PARENT.ROW].name,#A[PARENT.ROW].op_count,#A[PARENT.ROW].op_avg}}[ROWS(#A)]}.#B' % (op),
            'pathnames': statsfs,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@perf_grp.command(name='top_ops', help="Show filesystem ops consuming the most time by share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_top_ops(ctx, *args, **kwargs):
    statsfs = _dot_stats_files_paths(kwargs['pathnames'])
    eval_args = {
            'exp': '{(fs_stats.op_stats-get_tag("old_stats")),TOP100_TABLE{|::KEY={#A[PARENT.ROW].op_time,#A[PARENT.ROW].name,#A[PARENT.ROW].op_count,#A[PARENT.ROW].op_time,#A[PARENT.ROW].op_avg}}[ROWS(#A)]}.#B',
            'pathnames': statsfs,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@perf_grp.command(name='flushes', help="Counter for flush transactions by share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_flushes(ctx, *args, **kwargs):
    statsfs = _dot_stats_files_paths(kwargs['pathnames'])
    eval_args = {
            'exp': 'sum({|::#A=(fs_stats.op_stats-get_tag("old_stats"))[ROW].flush_count}[ROWS(fs_stats.op_stats)])',
            'pathnames': statsfs,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

#
# Bulk data dumpers
#
@click.group(name='dump', help="[sub] Dump info about various items", cls=OrderedGroup)
def dump_grp():
    pass
cli.add_command(dump_grp)

@dump_grp.command(name='inode', help="inode metadata")
@click.option('--full', is_flag=True, help="Include all available details")
@param_paths
@click.pass_context
def do_inode_dump(ctx, full, *args, **kwargs):
    eval_args = {
            #'force_json': True,
            'exp': 'DUMP_INODE',
            'recursive': True,
            'raw': True,
        }
    if full:
        eval_args['exp'] = "THIS"
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@dump_grp.command(name='iinfo', help="Alternative inode details, always in JSON format")
@param_paths
@click.pass_context
def do_inode_info(ctx, *args, **kwargs):
    _cmd_retcode(hss.inode_info, **kwargs)

@dump_grp.command(name='share', help="Full share(s) metadata")
@click.option('--filter-volume', nargs=1, help="Only report files that have an instance on this volume, provide volume name")
@param_sharepaths
@click.pass_context
def do_share_dump(ctx, filter_volume, *args, **kwargs):
    eval_args = {
            'exp': 'DUMP_INODE',
            'recursive': True,
            'raw': True,
        }
    kwargs.update(eval_args)
    if filter_volume is not None:
        kwargs['exp'] = 'dump_inode_on(storage_volume("%s"))' % (filter_volume)
    _cmd_retcode(hss.eval, **kwargs)

@dump_grp.command(name='misaligned', help="Dump details about misaligned files on the share(s)")
@param_sharepaths
@click.pass_context
def do_misaligned_files(ctx, *args, **kwargs):
    eval_args = {
            'exp': 'IS_FILE and overall_alignment!=alignment("aligned")?dump_inode',
            'recursive': True,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@dump_grp.command(name='threat', help="Dump details about files that are a virus threat on the share(s)")
@param_sharepaths
@click.pass_context
def do_threat_files(ctx, *args, **kwargs):
    eval_args = {
            'exp': 'IS_FILE and attributes.virus_scan==virus_scan_state("THREAT")?dump_inode',
            'recursive': True,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@dump_grp.command(name='map_file_to_obj', help="For --native object volumes, dump a mapping between file path and object volume path")
@click.argument('bucket_name', nargs=1, required=True)
@param_sharepaths
@click.pass_context
def do_dump_map_file_to_obj(ctx, bucket_name, *args, **kwargs):
    eval_args = {
            'exp': '{instances[|volume=storage_volume("%s")],!ISNA(#A)?{PATH,#A.PATH}}.#B' % (bucket_name),
            'recursive': True,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@dump_grp.command(name='files_on_volume', help="List all files that have data on the specified volume per share(s)")
@click.argument('volume_name', nargs=1, required=True)
@param_sharepaths
@click.pass_context
def do_dump_files_on_volume(ctx, volume_name, *args, **kwargs):
    eval_args = {
            'exp': '{instances[|volume=storage_volume("%s")],!ISNA(#A)?{PATH}}.#B' % (volume_name),
            'recursive': True,
        }
    kwargs.update(eval_args)
    _cmd_retcode(hss.eval, **kwargs)

@dump_grp.command(name='volumes', help="List available volumes in the cluster")
@param_path
@click.pass_context
def do_dump_volume_list(ctx, path, *args, **kwargs):
    # Another option to do the volume select:
    # exp: "(INDEXED_TABLE{|::#A=STORAGE_VOLUMES[ROW].VOLUME_STATUS!=STORAGE_VOLUME_STATUS('REMOVED'),|::#B=STORAGE_VOLUMES[ROW].NAME}[ROWS(STORAGE_VOLUMES)])[|#A=TRUE].#B" .
    # This builds an indexed table with the first column(#A)  being the
    # predicate and the second column (#B) being the volume name.  The table is
    # the same number of rows as there are storage volumes.  Then we select  #B
    # where #A is true
    #
    # The |::<col>= syntax is how you set every row in the column to a specific formula.
    # So :: means every row.
    kwargs['pathnames'] = [ path ]
    eval_args = {
            'exp': 'STORAGE_VOLUMES',
            'force_json': True,
        }
    kwargs.update(eval_args)
    hs_res = hs_eval(**kwargs)[path]
    if ctx.obj.dry_run:
        json_res = []
    else:
        json_res = json.loads(''.join(hs_res))['STORAGE_VOLUMES_TABLE']

    volumes = []
    for vol_json in json_res:
        if 'VOLUME_STATUS' not in vol_json:
            if 'Data Mover' not in vol_json['NAME']:
                print()
                print("ERROR, VOLUME_STATUS not found in")
                pprint.pprint(vol_json)
            continue
        if vol_json['VOLUME_STATUS']['HAMMERSCRIPT'] != "STORAGE_VOLUME_STATUS('REMOVED')":
            volumes.append(vol_json['NAME'])
    if ctx.obj.output_json:
        print(json.dumps(volumes))
    else:
        print('\n'.join(volumes))

@dump_grp.command(name='volume_groups', help="List available volume_groups")
@param_path
@click.pass_context
def do_dump_volume_group_list(ctx, path, *args, **kwargs):
    kwargs['pathnames'] = [ path ]
    eval_args = {
            'exp': 'VOLUME_GROUPS.NAME',
            'force_json': True,
        }
    kwargs.update(eval_args)

    hs_res = hs_eval(**kwargs)[path]
    if ctx.obj.dry_run:
        json_res = []
    else:
        json_res = json.loads(''.join(hs_res))['VOLUME_GROUPS_TABLE']

    vgs = []
    for vg_json in json_res:
        vgs.append(vg_json['NAME'])

    if ctx.obj.output_json:
        print(json.dumps(vgs))
    else:
        print('\n'.join(vgs))

@dump_grp.command(name='objectives', help="List available objectives")
@param_path
@click.pass_context
def do_dump_objectives_list(ctx, path, *args, **kwargs):
    kwargs['pathnames'] = [ path ]
    eval_args = {
            'exp': 'SMART_OBJECTIVES.NAME',
            'force_json': True,
        }
    kwargs.update(eval_args)

    hs_res = hs_eval(**kwargs)[path]
    if ctx.obj.dry_run:
        json_res = []
    else:
        json_res = json.loads(''.join(hs_res))['SMART_OBJECTIVES_TABLE']

    objs = []
    for obj_json in json_res:
        if obj_json['NAME'].startswith('__z_objective'):
            # deleted objective
            continue
        objs.append(obj_json['NAME'])

    if ctx.obj.output_json:
        print(json.dumps(objs))
    else:
        print('\n'.join(objs))

#
# GNS Replication sites
#
@click.group(name='keep-on-site', help="[sub] sites in the GNS to keep copies of the data on", cls=OrderedGroup)
def keep_on_site():
    pass
cli.add_command(keep_on_site)

# only good for single share, but get new invocation for each path
_GNS_PARTICIPANT_SITE_NAMES_CACHE=None
@click.pass_context
def _gns_participant_site_names(ctx, pathnames=['.'], force=False, **kwargs):
    global _GNS_PARTICIPANT_SITE_NAMES_CACHE
    if not force and _GNS_PARTICIPANT_SITE_NAMES_CACHE is not None:
        return _GNS_PARTICIPANT_SITE_NAMES_CACHE
    eval_args = {
        'exp': 'THIS.PARTICIPANTS',
        'force_json': True,
        'pathnames': pathnames[:1],
    }
    eval_res = hs_eval(**eval_args)[pathnames[0]]
    if ctx.obj.dry_run:
        _GNS_PARTICIPANT_SITE_NAMES_CACHE = [ 'dry_run_test_site1', 'dry_run_test_site2' ]
    else:
        json_res = json.loads(''.join(eval_res))['PARTICIPANTS_TABLE']

        _GNS_PARTICIPANT_SITE_NAMES_CACHE = []
        for site_json in json_res:
            _GNS_PARTICIPANT_SITE_NAMES_CACHE.append(site_json['SITE_NAME'])

    return _GNS_PARTICIPANT_SITE_NAMES_CACHE

def _completion_gns_participant_site_names(ctx, args, incomplete):
    # XXX Upgrade to click 8 to get shell_complete=
    pass

param_site_name = group_decorator(
            # Upgrade to click 8 to get shell_complete=
            #click.argument('name', metavar='site_name', nargs=1, required=True, shell_complete=_completion_gns_participant_site_names),
            click.argument('name', metavar='site_name', nargs=1, required=True),
        )

@keep_on_site.command(name='available', help="List sites names participating in this share")
@param_sharepaths
@click.pass_context
def do_gns_sites(ctx, *args, **kwargs):
    sites = _gns_participant_site_names(**kwargs)

    if ctx.obj.output_json:
        print(json.dumps(sites))
    else:
        print('\n'.join(sites))


@keep_on_site.command(name='list', help="list GNS sites with keep-on rules")
@param_eval
@param_read
@param_defaults
def do_gns_keep_on_list(ctx, *args, **kwargs):
    _cmd_retcode(hss.sites_keep_on_list, **kwargs)

@keep_on_site.command(name='has', help="Is there already a keep-on rule for the specified GNS site?")
@param_eval
@param_read
@param_site_name
@param_defaults
def do_gns_keep_on_has(ctx, *args, **kwargs):
    _cmd_retcode(hss.sites_keep_on_has, **kwargs)

@keep_on_site.command(name='delete', help="remove a GNS site keep-on rule")
@param_site_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_gns_keep_on_del(ctx, *args, **kwargs):
    if kwargs['name'] not in _gns_participant_site_names(**kwargs):
        errmsg = "'%s' is not a valid site name\n" % (kwargs['name'])
        raise click.UsageError(errmsg, ctx)
    _cmd_retcode(hss.sites_keep_on_del, **kwargs)

@keep_on_site.command(name='add', help="add a GNS site keep-on rule")
@param_site_name
@param_recursive
@param_nonfiles
@param_defaults
def do_gns_keep_on_add(ctx, *args, **kwargs):
    if kwargs['name'] not in _gns_participant_site_names(**kwargs):
        errmsg = "'%s' is not a valid site name\n" % (kwargs['name'])
        raise click.UsageError(errmsg, ctx)
    _cmd_retcode(hss.sites_keep_on_add, **kwargs)



### List XXX all locations (share root, directory, files) that have a local objective
### List XXX all locations (share root, directory, files) that have a tag/attribute/etc
### List XXX all locations (share root, directory, files) that have a gns keep-on

#
# Setup aliases
#

ALIAS_MAPPINGS = {
        'attribute': ('attributes', 'attr', 'attrs'),
        'tag': ('tags', ),
        'label': ('labels', 'lab'),
        'available': ('avail',),
        'keyword': ('keywords',),
        'delete': ('del',),
        'assimilation': ('assim',),
        'alignment': ('align',),
        'collsum': ('collsums', 'colsum', 'colsums'),
        'objective': ('objectives', 'obj', 'objs'),
        'rekognition-tag': ('rekognition-tags', ),
        'keep-on-site': ('keep-on-sites', ),
}
def _alias_mappings(cmd):
    for subname, subcmd in cmd.commands.items():
        if subname in ALIAS_MAPPINGS:
            cmd.add_alias(subname, *ALIAS_MAPPINGS[subname])
        if isinstance(subcmd, OrderedGroup):
            _alias_mappings(subcmd)

_alias_mappings(cli)


if __name__ == '__main__':
    cli()
