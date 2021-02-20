#!/usr/bin/env python
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
import functools
import sys
import os
import cStringIO as StringIO
import json
import pprint
import click
import hstk.hsscript as hss


# Helper object for containing global settings to be passed with context
class HSGlobals(object):
    def __init__(self, verbose=False, dry_run=False, output_json=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.output_json = output_json



class OrderedGroup(click.Group):
    """
    Keep the order items are added in for --help output
    """

    def __init__(self, commands=None, name=None, **kwargs):
        self._ordered_commands = []
        if commands is not None:
            for cmd in commands:
                self._ordered_commands.append(cmd.name)
        super(OrderedGroup, self).__init__(name=name, commands=commands, **kwargs)

    def list_commands(self, ctx):
        return self._ordered_commands

    def add_command(self, cmd, name=None):
        if name is not None:
            self._ordered_commands.append(name)
        else:
            self._ordered_commands.append(cmd.name)
        super(OrderedGroup, self).add_command(cmd, name=None)

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
@click.option('-j', '--json', 'output_json', is_flag=True, help="Use JSON formatted output")
@click.option('--cmd-tree', is_flag=True, help="Show help for available commands")
@click.pass_context
def cli(ctx, verbose, dry_run, output_json, cmd_tree):
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


    ctx.obj = HSGlobals(verbose=verbose, dry_run=dry_run,output_json=output_json)
    if ctx.obj.verbose > 1:
        print ('V: verbose: ' + str(verbose))
        print ('V: dry_run: ' + str(dry_run))
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

        self.symlink_name = None
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

        if self.checkopt('symlink', self.kwargs):
            self.symlink_name = self.kwargs['symlink']

        exp = None
        if self.checkopt('exp_file', self.kwargs):
            fn = self.kwargs['exp_file']
            with open(click.format_filename(self.kwargs['exp_file'])) as fd:
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


    def readlines(self):
        ret = {}
        for shadfile in self.paths:
            ret[shadfile] = []
            if self.verbose > 0 or self.dry_run:
                tag = 'V: '
                if self.dry_run:
                    tag = 'N: '
                print(tag + 'open(  '+ shadfile + '  )')
                if self.dry_run:
                    ret[shadfile].append("")
                    continue
            try:
                fd = open(shadfile)
            except IOError as e:
                # non-existant base file is caught in the arg parsing, don't have to handle here
                errstr = str(e)
                # For clarity, remove the extra random data added to the end to
                # avoid shadow file caching for the error message
                errstr = errstr.split('\u2215')[0]
                errstr = errstr.replace("u'", "")
                errstr = errstr.replace("'", "")
                raise click.ClickException(errstr)
            ret[shadfile].extend(fd.readlines())
            fd.close()
        return ret

    def mksymlink(self):
        ret = {}
        for shadfile in self.paths:
            ret[shadfile] = []
            symprint = 'symlink("'+ shadfile + '", "' + self.symlink_name + '")'
            if self.verbose > 0 or self.dry_run:
                tag = 'V: '
                if self.dry_run:
                    tag = 'N: '
                print(tag + symprint)
                if self.dry_run:
                    ret[shadfile].append("")
                    continue
            os.symlink(shadfile, self.symlink_name)
            ret[shadfile].append("")
        return ret

    def run(self):
        if self.symlink_name is not None:
            ret = self.mksymlink()
        else:
            ret = self.readlines()
        if self.outstream is not None:

            print_filenames = False
            if len(ret.keys()) > 1:
                print_filenames = True

            for k, v in ret.iteritems():
                if print_filenames:
                    self.outstream.write("##### " + k.split('?.')[0] + '\n')
                for line in v:
                    self.outstream.write(line)
            self.outstream.flush()
        if self.output_returns_error:
            for k, v in ret.iteritems():
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
        shadcmd = self.shadgen(**self.kwargs)
        for path in paths:
            if path[-1] != '/' and os.path.isdir(path):
                path += '/'
            self._paths.append(path + shadcmd)

    def checkopt(self, opt, optsdict):
        if opt in optsdict and optsdict[opt] not in (None, False):
            return True
        return False

def _param_defaults__pathnames_set_default(func):
    def wrapper(*args, **kwargs):
        if len(kwargs['pathnames']) == 0:
            vnprint('Setting default pathname to .')
            kwargs['pathnames'] = [ '.' ]
        func(*args, **kwargs)
    return wrapper
param_defaults = group_decorator(
            click.pass_context,
            click.option('--symlink', type=click.Path(exists=False), nargs=1, default=None, help="Create a symlink file with this name that encodes the shadow command"),
            click.argument('pathnames', nargs=-1, type=click.Path(exists=True, readable=False)),
            _param_defaults__pathnames_set_default
        )

param_sharepath = click.argument('sharepath', nargs=1, type=click.Path(exists=True, file_okay=False, readable=False), required=True, default=".")
param_sharepaths = click.argument('sharepaths', nargs=-1, type=click.Path(exists=True, file_okay=False, readable=False), required=True)
param_path = click.argument('path', nargs=1, type=click.Path(exists=True, readable=False), required=True, default=".")
param_paths = click.argument('paths', nargs=-1, type=click.Path(exists=True, readable=False), required=True)
param_dirpath = click.argument('dirpath', nargs=1, type=click.Path(exists=True, file_okay=False, readable=False), required=True, default=".")
param_dirpaths = click.argument('dirpaths', nargs=-1, type=click.Path(exists=True, file_okay=False, readable=False), required=True)
param_filepath = click.argument('filepath', nargs=1, type=click.Path(exists=True, dir_okay=False, readable=False), required=True)

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
    cmd = ShadCmd(hss.eval, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

def hs_eval(*args, **kwargs):
    # Run an eval command but return the results as a string rather than displaying
    kwargs['force_json'] = True
    orig_pathnames = kwargs['pathnames']

    ret = {}
    for path in orig_pathnames:
        kwargs['pathnames'] = [ path ]
        kwargs['outstream'] = StringIO.StringIO()
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
    cmd = ShadCmd(hss.sum, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

def hs_sum(*args, **kwargs):
    # Run an sum command but return the results as a string rather than displaying
    kwargs['force_json'] = True
    orig_pathnames = kwargs['pathnames']

    ret = {}
    for path in orig_pathnames:
        kwargs['pathnames'] = [ path ]
        kwargs['outstream'] = StringIO.StringIO()
        cmd = ShadCmd(hss.sum, kwargs)
        cmd.run()
        cmd.outstream.seek(0)
        ret[path] = [ x[:-1] for x in cmd.outstream.readlines() ]
    return ret



#
# Subcommands with noun verb, metadata and objectives
#

attribute_short_help = "[sub] inode metadata: schema yes, value yes"
@cli.group(short_help=attribute_short_help, cls=OrderedGroup)
def attribute():
    attribute_short_help + '\n\n' + """
    Attributes must exist in the attribute schema before being utilized, see XXX
    for schema management.  The value must also exist in the associated value
    schema for that atttribute.  Most values are string type (-s) unless it is a
    number than an expression (-e)

      ex: hs attribute set -n color -s blue path/to/file
    """
    pass

keyword_short_help = "[sub] inode metadata: schema no, value no"
@cli.group(short_help=keyword_short_help, cls=OrderedGroup)
def keyword():
    keyword_help = keyword_short_help + '\n\n' + """
    TODO XXX
    """
    pass

label_short_help = "[sub] inode metadata: schema hierarchical, value no"
@cli.group(short_help=label_short_help, cls=OrderedGroup)
def label():
    label_short_help + '\n\n' + """
    TODO XXX
    """
    pass

tag_short_help = "[sub] inode metadata: schema no, value yes"
@cli.group(short_help=tag_short_help, cls=OrderedGroup)
def tag():
    tag_short_help + '\n\n' + """
    TODO XXX
    """
    pass

rekognition_tag_short_help = "[sub] inode metadata: schema no, value yes"
@cli.group(short_help=rekognition_tag_short_help, cls=OrderedGroup)
def rekognition_tag():
    rekognition_tag_short_help + '\n\n' + """
    TODO XXX
    """
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
    cmd = ShadCmd(hss.attribute_list, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@tag.command(name='list', help="list all tags and values applied")
@param_eval
@param_read
@param_defaults
@param_unbound
def do_tag_list(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.tag_list, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@rekognition_tag.command(name='list', help="list all rekognition tags and values applied")
@param_eval
@param_read
@param_defaults
def do_rekognition_tag_list(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.rekognition_tag_list, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@keyword.command(name='list', help="list all keywords applied")
@param_eval
@param_read
@param_defaults
def do_keyword_list(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.keyword_list, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@label.command(name='list', help="list all labels applied")
@param_eval
@param_read
@param_defaults
def do_label_list(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.label_list, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@objective.command(name='list', help="list all (objective,expression) pairs assigned")
@param_eval
@param_objective_read
@param_defaults
def do_objective_list(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.objective_list, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)



@attribute.command(name='get', help="Get the attribute's value")
@param_eval
@param_read
@param_name
@param_unbound
@param_defaults
def do_attribute_get(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.attribute_get, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@attribute.command(name='has', help="Is the inode's attribute value non-empty")
@param_eval
@param_read
@param_name
@param_defaults
def do_attribute_has(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.attribute_get, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@tag.command(name='get', help="Get the tag's value")
@param_eval
@param_read
@param_name
@param_unbound
@param_defaults
def do_tag_get(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.tag_get, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@rekognition_tag.command(name='get', help="Get the rekognition tag's value")
@param_eval
@param_read
@param_name
@param_unbound
@param_defaults
def do_rekognition_tag_get(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.rekognition_tag_get, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@tag.command(name='has', help="Is the inode's tag value non-empty")
@param_eval
@param_read
@param_name
@param_defaults
def do_tag_has(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.tag_has, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@rekognition_tag.command(name='has', help="Is the inode's rekognition tag value non-empty")
@param_eval
@param_read
@param_name
@param_defaults
def do_rekognition_tag_has(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.rekognition_tag_has, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@keyword.command(name='has', help="Is the keyword assigned to the file")
@param_eval
@param_read
@param_name
@param_defaults
def do_keyword_has(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.keyword_has, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@label.command(name='has', help="Is the label assigned to the file")
@param_eval
@param_read
@param_name
@param_defaults
def do_label_has(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.label_has, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@objective.command(name='has', help="Get/list objective assignments")
@param_eval
@param_objective_read
@param_name
@param_value
@param_defaults
def do_objective_has(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.objective_has, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)



@attribute.command(name='delete', help="remove attribute values from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_attribute_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.attribute_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@tag.command(name='delete', help="remove tag values from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_tag_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.tag_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@rekognition_tag.command(name='delete', help="remove rekognition tag values from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_rekognition_tag_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.rekognition_tag_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@keyword.command(name='delete', help="remove keywords from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_keyword_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.keyword_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@label.command(name='delete', help="remove labels from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_defaults
def do_label_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.label_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@objective.command(name='delete', help="remove (objective,expression) pair from inode(s)")
@param_name
@param_force
@param_recursive
@param_nonfiles
@param_value
@param_defaults
def do_objective_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.objective_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)



@keyword.command(name='add', help="add a keyword to inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_defaults
def do_keyword_add(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.keyword_add, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@label.command(name='add', help="add a label to inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_defaults
def do_label_add(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.label_add, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@attribute.command(name='set', help="Add/Set value of attribute on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_attribute_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.attribute_set, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@attribute.command(name='add', help="Add/Set value of attribute on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_attribute_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.attribute_set, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@tag.command(name='set', help="Add/Set value of tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_tag_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.tag_set, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@rekognition_tag.command(name='set', help="Add/Set value of rekognition tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_rekognition_tag_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.rekognition_tag_set, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@tag.command(name='add', help="Add/Set value of tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_tag_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.tag_set, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@rekognition_tag.command(name='add', help="Add/Set value of rekognition tag on inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_rekognition_tag_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.rekognition_tag_set, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@objective.command(name='add', help="Add (objective,expression) pair to inode(s)")
@param_name
@param_recursive
@param_nonfiles
@param_value
@param_defaults
@param_unbound
def do_objective_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.objective_add, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)


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
        if kwargs[opt] != None:
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

    if os.path.isfile(dest):
        dest_is_file = True
    else:
        dest_is_file = False

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
            versions[src] = int(versions[src][0])
            versions[dest] = int(versions[dest][0])
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
@param_sharepaths
@click.argument('collection', nargs=1, required=True, default="all")
@click.option('--collation', nargs=1, required=False)
@click.pass_context
def do_collection_sum(ctx, sharepaths, collection, collation, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    if collation is None:
        eval_args = {
                'exp': 'collection_sums("%s")' % (collection),
            }
    else:
        eval_args = {
                'exp': 'collection_sums("%s")[SUMMATION("%s")],#B' % (collection, collation),
            }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)



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
def do_assim_status(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'assimilation_details',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@status.command(name='csi', help="Details about the kubernetes CSI")
@param_sharepaths
@click.pass_context
def do_csi_status(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'attributes.csi_details',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@status.command(name='collections', help="Collections present in the share")
@param_sharepath
@click.pass_context
def do_collections_list(ctx, sharepaths, *args, **kwargs):
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'collections',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@status.command(name='errors', help="Files in the share with errors")
@param_sharepaths
@click.option('--dump', is_flag=True, help="Dump inode details, only on files in dir+dirpath")
@click.pass_context
def do_errored_files(ctx, sharepaths, dump, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    if dump:
        sum_args = {
                'exp': '(IS_FILE AND ERRORS)?SUMS_TABLE{|KEY=ERRORS,|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
            }
        kwargs.update(sum_args)
        ctx.invoke(do_sum, **kwargs)
    else:
        eval_args = {
                'exp': 'IS_FILE and errors!=0?dump_inode',
                'recursive': True,
            }
        kwargs.update(eval_args)
        ctx.invoke(do_eval, **kwargs)

@status.command(name='open', help="Files open each dir(s)")
@param_dirpaths
@click.pass_context
def do_show_open_files(ctx, dirpaths, *args, **kwargs):
    if not dirpaths:
        dirpaths = [ '.' ]
    kwargs['pathnames'] = dirpaths
    sum_args = {
            'exp': '(IS_FILE AND IS_OPEN)?{1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@status.command(name='replication', help="Replication progress for the share(s)")
@param_sharepaths
@click.pass_context
def do_replication_status(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'replication_details',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@status.command(name='sweeper', help="Progress of sweeper (checks file placement) for each share(s)")
@param_sharepaths
@click.pass_context
def do_sweeper_status(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'sweep_details',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@status.command(name='volume', help="Health of volumes backing the share(s)")
@param_sharepaths
@click.pass_context
def do_volume_health(ctx, sharepaths, *args, **kwargs):
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': '{|::#A=storage_volumes.name[row],|::#B=storage_volumes.volume_status[row],|::#C=storage_volumes.oper_status[row]}[rows(storage_volumes)]',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)



#
# Capacity and inode usage
#
@click.group(name='usage', short_help="[sub] Resource utilization such as capacity or inode", cls=OrderedGroup)
def usage():
    pass
cli.add_command(usage)

@usage.command(name='alignment', help="Alignment state of files each file(s) of files in dir(s)")
@param_paths
@click.option('--top-files', is_flag=True, help="include largest files in each alignment state")
@click.pass_context
def do_file_alignment(ctx, paths, top_files, *args, **kwargs):
    kwargs['pathnames'] = paths
    if top_files:
        sum_args = {
                'exp': 'IS_FILE?SUMS_TABLE{|KEY=OVERALL_ALIGNMENT,|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
            }
    else:
        sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY=OVERALL_ALIGNMENT,|VALUE=1}',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='virus-scan', help="Virus scan state of files each file(s) of files in dir(s)")
@param_paths
@click.option('--top-files', is_flag=True, help="include largest files in each virus scan state")
@click.pass_context
def do_file_virus_scan(ctx, paths, top_files, *args, **kwargs):
    kwargs['pathnames'] = paths
    if top_files:
        sum_args = {
                'exp': 'IS_FILE?SUMS_TABLE{|KEY=ATTRIBUTES.VIRUS_SCAN,|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
            }
    else:
        sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY=ATTRIBUTES.VIRUS_SCAN,|VALUE=1}',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='online', help="Summary of files on NAS volumes in the dir")
@param_dirpaths
@click.pass_context
def do_online_files(ctx, dirpaths, *args, **kwargs):
    if not dirpaths:
        dirpaths = [ '.' ]
    kwargs['pathnames'] = dirpaths
    sum_args = {
            'exp': 'IS_ONLINE?{1FILE,SPACE_USED,TOP10_TABLE{{space_used,DPATH}}}',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='volume', help="Usage for each volume backing each dir(s)")
@param_paths
@click.option('--top-files', is_flag=True, help="Show largest files on each volume")
@click.option('--deep', is_flag=True, help="Might take a long time, XXX")
@click.pass_context
def do_volume_usage(ctx, paths, top_files, deep, *args, **kwargs):
    if not paths:
        paths = [ '.' ]
    kwargs['pathnames'] = paths
    sum_args = {
            'exp': 'IS_FILE?ROWS(INSTANCES)?SUMS_TABLE{|::KEY=INSTANCES[ROW].VOLUME,|::VALUE=1}[ROWS(INSTANCES)]:SUMS_TABLE{|KEY=#EMPTY,|::VALUE=1}',
        }
    kwargs.update(sum_args)
    if top_files:
        kwargs['exp'] = 'IS_FILE?ROWS(INSTANCES)?SUMS_TABLE{|::KEY=INSTANCES[ROW].VOLUME,|::VALUE={1FILE,INSTANCES[ROW].SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}[ROWS(INSTANCES)]:SUMS_TABLE{|KEY=#EMPTY,|::VALUE={1FILE, SPACE_USED, TOP10_TABLE{{space_used,dpath}}}}'
    if deep:
        kwargs['exp'] = 'IS_FILE?ROWS(INSTANCES)?SUMS_TABLE{|::KEY=INSTANCES[ROW].VOLUME,|::VALUE={1FILE,INSTANCES[ROW].SPACE_USED,TOP100_TABLE{{space_used,dpath}}}}[ROWS(INSTANCES)]:SUMS_TABLE{|KEY=#EMPTY,|::VALUE={1FILE, SPACE_USED, TOP100_TABLE{{space_used,dpath}}}}'
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='user', help="Users consuming the most capacity in each dir(s)")
@param_dirpaths
@click.option('--details', is_flag=True, help="Include details like largest files per user")
@click.pass_context
def do_users_top_usage(ctx, dirpaths, details, *args, **kwargs):
    if not dirpaths:
        dirpaths = [ '.' ]
    kwargs['pathnames'] = dirpaths
    sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY={OWNER,OWNER_GROUP},|VALUE=SPACE_USED}',
        }
    if details:
        sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|KEY={OWNER,OWNER_GROUP},|VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='objectives', help="Objectives applied and capacity managed by dir(s)")
@param_dirpaths
@click.pass_context
def do_objectives_usage(ctx, dirpaths, *args, **kwargs):
    kwargs['pathnames'] = dirpaths
    sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{|::KEY=LIST_OBJECTIVES_ACTIVE[ROW],|::VALUE={1FILE,SPACE_USED,TOP10_TABLE{{space_used,dpath}}}}[ROWS(LIST_OBJECTIVES_ACTIVE)]',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='mime_tags', help="All tags added by mime discovery on dir(s)")
@param_dirpaths
@click.pass_context
def do_list_mime_tags(ctx, dirpaths, *args, **kwargs):
    if not dirpaths:
        dirpaths = [ '.' ]
    kwargs['pathnames'] = dirpaths
    sum_args = {
            'exp': 'IS_FILE?SUMS_TABLE{attributes.mime.string,{1FILE,SPACE_USED,TOP10_TABLE{{SPACE_USED,DPATH}}}}',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='rekognition_tags', help="All tags added by Rekognition on dir(s)")
@param_dirpaths
@click.pass_context
def do_list_rekognition_tags(ctx, dirpaths, *args, **kwargs):
    if not dirpaths:
        dirpaths = [ '.' ]
    kwargs['pathnames'] = dirpaths
    sum_args = {
            'exp': 'IS_FILE?ISTABLE(LIST_REKOGNITION_TAGS)?SUMS_TABLE{|::KEY=LIST_REKOGNITION_TAGS()[ROW].NAME,|::VALUE={1FILE,TOP10_TABLE{{LIST_REKOGNITION_TAGS()[ROW].value,dpath}}}}[ROWS(LIST_REKOGNITION_TAGS())]',
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

@usage.command(name='dirs', help="Number of subdirectories under specified directory(ies), not including that directory")
@param_dirpaths
@click.pass_context
def do_dirs_count(ctx, dirpaths, *args, **kwargs):
    # Also, an efficient way to follow an assimilation, this will block until it completes
    if not dirpaths:
        dirpaths = [ '.' ]
    kwargs['pathnames'] = dirpaths
    sum_args = {
            'exp': '1',
            'nonfiles': True,
        }
    kwargs.update(sum_args)
    ctx.invoke(do_sum, **kwargs)

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
def _dot_stats_files(ctx, paths):
    statsfs = {}

    for path in paths:
        # eval -e path to find the root of the share, create .stats there?
        statsf = os.path.join(sharepath, '.stats')

        if ctx.obj.dry_run:
            vnprint('dry run, not creating .stats file ' + statsf)
        elif not os.path.exists(statsf):
            vnprint('creating .stats file ' + statsf)
            with open(statsf) as fd:
                pass
        statsfs[path] = statsf

    return statsfs

@perf_grp.command(name='clear', help="Clear op/perf counters on share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_clear(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    statsfs = _dot_stats_files(kwargs['pathnames'])
    tag_args = {
            'exp': 'fs_stats.op_stats',
        }
    kwargs.update(tag_args)
    ctx.invoke(do_tag_add, **kwargs)

@perf_grp.command(name='top_calls', help="Show filesystem calls consuming the most time on share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_top_calls(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    statsfs = _dot_stats_files(kwargs['pathnames'])
    eval_args = {
            'exp': '{(fs_stats.op_stats-get_tag("old_stats")),TOP100_TABLE{|::KEY={#A[PARENT.ROW].op_count,#A[PARENT.ROW].name,#A[PARENT.ROW].op_count,#A[PARENT.ROW].op_time,#A[PARENT.ROW].op_avg}}[ROWS(#A)]}.#B',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@perf_grp.command(name='top_funcs', help="Top time consuming functions on share(s)")
@param_sharepath
@click.option('--op', nargs=1, default='all', help="Restrict to reporting to funcs in a specific op")
@click.pass_context
def do_report_stats_funcs(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    statsfs = _dot_stats_files(kwargs['pathnames'])
    eval_args = {
            'exp': '{(FS_STATS.OP_STATS-get_tag("old_stats"))[|NAME="%s"].func_stats,TOP100_TABLE{|::KEY={#A[PARENT.ROW].op_time,#A[PARENT.ROW].name,#A[PARENT.ROW].op_count,#A[PARENT.ROW].op_avg}}[ROWS(#A)]}.#B' % (op),
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@perf_grp.command(name='top_ops', help="Show filesystem ops consuming the most time by share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_top_ops(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    statsfs = _dot_stats_files(kwargs['pathnames'])
    eval_args = {
            'exp': '{(fs_stats.op_stats-get_tag("old_stats")),TOP100_TABLE{|::KEY={#A[PARENT.ROW].op_time,#A[PARENT.ROW].name,#A[PARENT.ROW].op_count,#A[PARENT.ROW].op_time,#A[PARENT.ROW].op_avg}}[ROWS(#A)]}.#B',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@perf_grp.command(name='flushes', help="Counter for flush transactions by share(s)")
@param_sharepaths
@click.pass_context
def do_report_stats_flushes(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    statsfs = _dot_stats_files(kwargs['pathnames'])
    eval_args = {
            'exp': 'sum({|::#A=(fs_stats.op_stats-get_tag("old_stats"))[ROW].flush_count}[ROWS(fs_stats.op_stats)])',
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)



#
# Bulk data dumpers
#
@click.group(name='dump', help="[sub] Dump info about various items", cls=OrderedGroup)
def dump_grp():
    pass
cli.add_command(dump_grp)

@dump_grp.command(name='inode', help="inode metadata")
@param_paths
@click.option('--full', is_flag=True, help="Include all available details")
@click.pass_context
def do_inode_dump(ctx, paths, full, *args, **kwargs):
    if not paths:
        paths = [ '.' ]
    kwargs['pathnames'] = paths
    eval_args = {
            #'force_json': True,
            'exp': 'DUMP_INODE',
            'recursive': True,
            'raw': True,
        }
    if full:
        eval_args['exp'] = "THIS"
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@dump_grp.command(name='iinfo', help="Alternative inode details, always in JSON format")
@param_paths
@click.pass_context
def do_inode_info(ctx, paths, *args, **kwargs):
    if not paths:
        paths = [ '.' ]
    kwargs['pathnames'] = paths
    cmd = ShadCmd(hss.inode_info, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@dump_grp.command(name='share', help="Full share(s) metadata")
@click.option('--filter-volume', nargs=1, help="Only report files that have an instance on this volume, provide volume name")
@param_sharepaths
@click.pass_context
def do_share_dump(ctx, sharepaths, filter_volume, *args, **kwargs):
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'DUMP_INODE',
            'recursive': True,
            'raw': True,
        }
    kwargs.update(eval_args)
    if filter_volume is not None:
        kwargs['exp'] = 'dump_inode_on(storage_volume("%s"))' % (filter_volume)
    ctx.invoke(do_eval, **kwargs)

@dump_grp.command(name='misaligned', help="Dump details about misaligned files on the share(s)")
@param_sharepaths
@click.pass_context
def do_misaligned_files(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'IS_FILE and overall_alignment!=alignment("aligned")?dump_inode',
            'recursive': True,
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@dump_grp.command(name='threat', help="Dump details about files that are a virus threat on the share(s)")
@param_sharepaths
@click.pass_context
def do_threat_files(ctx, sharepaths, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': 'IS_FILE and attributes.virus_scan==virus_scan_state("THREAT")?dump_inode',
            'recursive': True,
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@dump_grp.command(name='map_file_to_obj', help="For --native object volumes, dump a mapping between file path and object volume path")
@click.argument('bucket_name', nargs=1, required=True)
@param_sharepaths
@click.pass_context
def do_dump_map_file_to_obj(ctx, sharepaths, bucket_name, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': '{instances[|volume=storage_volume("%s")],!ISNA(#A)?{PATH,#A.PATH}}.#B' % (bucket_name),
            'recursive': True,
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

@dump_grp.command(name='files_on_volume', help="List all files that have data on the specified volume per share(s)")
@click.argument('volume_name', nargs=1, required=True)
@param_sharepaths
@click.pass_context
def do_dump_files_on_volume(ctx, sharepaths, volume_name, *args, **kwargs):
    if not sharepaths:
        sharepaths = [ '.' ]
    kwargs['pathnames'] = sharepaths
    eval_args = {
            'exp': '{instances[|volume=storage_volume("%s")],!ISNA(#A)?{PATH}}.#B' % (volume_name),
            'recursive': True,
        }
    kwargs.update(eval_args)
    ctx.invoke(do_eval, **kwargs)

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



if __name__ == '__main__':
    cli()
