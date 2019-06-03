#!/usr/bin/env python
#
# Copyright 2019 Hammerspace
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
import click
import functools
import sys
import os
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



#
# Top level group for subcommands
#
@click.group(cls=OrderedGroup)
@click.option('-v', '--verbose', count=True, help="Debug output")
@click.option('-n', '--dry-run', is_flag=True, help="Don't operate on files")
@click.option('-j', '--json', 'output_json', is_flag=True, help="Use JSON formatted output")
@click.pass_context
def cli(ctx, verbose, dry_run, output_json):
    """
    Top level function to kick of click parsing.
    verbose and dry-run are to be respected globally
    """
    ctx.obj = HSGlobals(verbose=verbose, dry_run=dry_run,output_json=output_json)
    if ctx.obj.verbose > 1:
        print ('V: verbose: ' + str(verbose))
        print ('V: dry_run: ' + str(dry_run))
        print ('V: output_json: ' + str(output_json))

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
        self.output_json = self.ctx.obj.output_json
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
            with open(shadfile) as fd:
                ret[shadfile].extend(fd.readlines())
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

param_defaults = group_decorator(
            click.pass_context,
            click.option('--symlink', type=click.Path(exists=False), nargs=1, default=None, help="Create a symlink file with this name that encodes the shadow command"),
            click.argument('pathnames', nargs=-1, type=click.Path(exists=True), required=True),
        )

param_recursive = click.option('-r', '--recursive', is_flag=True, help="Apply recursively")
param_force = click.option('--force', is_flag=True, help="Force delete (suppress not found errors)")

param_eval = group_decorator(
            param_recursive,
            click.option('--raw', is_flag=True, help="Print raw output"),
            click.option('--compact', is_flag=True, help="Print compact output"),
        )

param_sum = group_decorator(
            click.option('--raw', is_flag=True, help="Print raw output"),
            click.option('--compact', is_flag=True, help="Print compact output"),
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



@cli.command(name='sum', help="Perform fast calculations on a set of files")
@param_sum
@param_value
@param_defaults
def do_sum(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.sum, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)



#
# Subcommands with noun verb, metadata and objectives
#

attribute_short_help = "inode metadata: schema yes, value yes"
@cli.group(short_help=attribute_short_help)
def attribute():
    attribute_short_help + '\n\n' + """
    Attributes must exist in the attribute schema before being utilized, see XXX
    for schema management.  The value must also exist in the associated value
    schema for that atttribute.  Most values are string type (-s) unless it is a
    number than an expression (-e)

      ex: hs attribute set -n color -s blue path/to/file
    """
    pass

keyword_short_help = "inode metadata: schema no, value no"
@cli.group(short_help=keyword_short_help)
def keyword():
    keyword_help = keyword_short_help + '\n\n' + """
    TODO XXX
    """
    pass

label_short_help = "inode metadata: schema hierarchical, value no"
@cli.group(short_help=label_short_help)
def label():
    label_short_help + '\n\n' + """
    TODO XXX
    """
    pass

tag_short_help = "inode metadata: schema no, value yes"
@cli.group(short_help=tag_short_help)
def tag():
    tag_short_help + '\n\n' + """
    TODO XXX
    """
    pass

rekognition_tag_short_help = "inode metadata: schema no, value yes"
@cli.group(short_help=rekognition_tag_short_help)
def rekognition_tag():
    rekognition_tag_short_help + '\n\n' + """
    TODO XXX
    """
    pass

objective_short_help = "control file placement on backend storage"
@cli.group(short_help=objective_short_help)
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
@param_defaults
def do_attribute_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.attribute_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@tag.command(name='delete', help="remove tag values from inode(s)")
@param_name
@param_force
@param_recursive
@param_defaults
def do_tag_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.tag_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@rekognition_tag.command(name='delete', help="remove rekognition tag values from inode(s)")
@param_name
@param_force
@param_recursive
@param_defaults
def do_rekognition_tag_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.rekognition_tag_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@keyword.command(name='delete', help="remove keywords from inode(s)")
@param_name
@param_force
@param_recursive
@param_defaults
def do_keyword_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.keyword_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@label.command(name='delete', help="remove labels from inode(s)")
@param_name
@param_force
@param_recursive
@param_defaults
def do_label_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.label_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@objective.command(name='delete', help="remove (objective,expression) pair from inode(s)")
@param_name
@param_force
@param_recursive
@param_value
@param_defaults
def do_objective_del(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.objective_del, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)



@keyword.command(name='add', help="add a keyword to inode(s)")
@param_name
@param_recursive
@param_defaults
def do_keyword_add(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.keyword_add, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@label.command(name='add', help="add a label to inode(s)")
@param_name
@param_recursive
@param_defaults
def do_label_add(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.label_add, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)

@attribute.command(name='set', help="Add/Set value of attribute on inode(s)")
@param_name
@param_recursive
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
@param_value
@param_defaults
@param_unbound
def do_objective_set(ctx, *args, **kwargs):
    cmd = ShadCmd(hss.objective_add, kwargs)
    cmd.run()
    sys.exit(cmd.exit_status)



if __name__ == '__main__':
    cli()
