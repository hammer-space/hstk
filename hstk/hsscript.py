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

import sys
import random
reload(sys)
sys.setdefaultencoding('utf8')

class HSExp(object):
    def __init__(self, exp=None, string=False, input_json=False, unbound=False):
        self.exp = exp
        self.string = string
        self.input_json = input_json
        self.unbound = unbound

    def __str__(self):
        if self.unbound:
            ret = 'EXPRESSION(' + self.exp + ')'
        else:
            ret = self.exp

        if self.string:
            ret = '"' + ret + '"'
        return ret

_global_args = { 'json': False }
_eval_args = { 'recursive': False, 'nonfiles': False, 'raw': False, 'compact': False }
_eval_args.update(_global_args)
def _build_eval(**kwargs):
    tset = set()
    for tkey in _eval_args.keys():
        if kwargs[tkey]:
            tset.add(tkey)
    if 'compact' in tset and 'raw' in tset:
        raise RuntimeError("Select only one of compact / raw")
    ret = 'eval'        
    if 'compact' in tset:
        ret += '_compact'
    if 'raw' in tset:
        ret += '_raw'
    if 'nonfiles' in tset:
        ret += '_rec_nofiles'
    else:
        if 'recursive' in tset:
            ret += '_rec'
    if 'json' in tset:
        ret += '_json'
    return ret

_sum_args = { 'raw': False, 'compact': False, 'nonfiles': False }
_sum_args.update(_global_args)
def _build_sum(**kwargs):
    tset = set()
    for tkey in _sum_args.keys():
        if kwargs[tkey]:
            tset.add(tkey)
    if 'compact' in tset and 'raw' in tset:
        raise RuntimeError("Select only one of compact / raw")
    ret = 'sum'
    if 'compact' in tset:
        ret += '_compact'
    if  'raw' in tset:
        ret += '_raw'
    if 'nonfiles' in tset:
        ret += '_nofiles'
    if 'json' in tset:
        ret += '_json'
    return ret

_set_args = { 'recursive': False , 'nonfiles': False }
def _build_set(**kwargs):
    tset = set()
    for tkey in _set_args.keys():
        if kwargs[tkey]:
            tset.add(tkey)
    ret = 'set'
    if 'nonfiles' in tset:
        ret += '_rec_nofiles'
    else:
        if 'recursive' in tset:
            ret += '_rec'
    return ret

_inheritance_args = { 'local': False, 'inherited': False, 'object': False, 'active': False, 'effective': False, 'share': False }
def _build_inheritance(**kwargs):
    tset = set()
    for tkey in _inheritance_args.keys():
        if kwargs[tkey]:
            tset.add(tkey)
    if 'local' in tset and 'inherited' in tset:
        raise RuntimeError("Select only one of local / inherited")

    if 'local' in tset and 'object' in tset:
        raise RuntimeError("Select only one of local / object")

    if 'local' in tset and 'active' in tset:
        raise RuntimeError("Select only one of local / active")

    if 'local' in tset and 'effective' in tset:
        raise RuntimeError("Select only one of local / effective")

    if 'local' in tset and 'share' in tset:
        raise RuntimeError("Select only one of local / share")

    if 'inherited' in tset and 'object' in tset:
        raise RuntimeError("Select only one of inherited / object")

    if 'inherited' in tset and 'active' in tset:
        raise RuntimeError("Select only one of inherited / active")

    if 'inherited' in tset and 'effective' in tset:
        raise RuntimeError("Select only one of inherited / effective")

    if 'inherited' in tset and 'share' in tset:
        raise RuntimeError("Select only one of inherited / share")

    if 'object' in tset and 'active' in tset:
        raise RuntimeError("Select only one of object / active")

    if 'object' in tset and 'effective' in tset:
        raise RuntimeError("Select only one of object / effective")

    if 'object' in tset and 'share' in tset:
        raise RuntimeError("Select only one of object / share")

    if 'active' in tset and 'effective' in tset:
        raise RuntimeError("Select only one of active / effective")

    if 'active' in tset and 'share' in tset:
        raise RuntimeError("Select only one of active / share")

    if 'effective' in tset and 'share' in tset:
        raise RuntimeError("Select only one of effective / share")

    if tset == set():
        return ''
    if tset == set( ( 'local', ) ):
        return '_local'
    if tset == set( ( 'inherited', ) ):
        return '_inherited'
    if tset == set( ( 'object', ) ):
        return '_object'
    if tset == set( ( 'active', ) ):
        return '_active'
    if tset == set( ( 'effective', ) ):
        return '_effective'
    if tset == set( ( 'share', ) ):
        return '_share'
    raise RuntimeError("Shouldn't reach this")

def _do_update_kwargs(def_kwargs, kwargs):
    for k, v in def_kwargs.iteritems():
        if k not in kwargs:
            kwargs[k] = v

def _clean_str(value):
    """Allow the use of / in filenames by remapping the character to a unicode character Hammerscript treats as /"""
    value += "/*" + hex(random.randint(0,99999999)) + "*/"
    return value.replace('/', unichr(0x2215).encode('UTF-8'))


def _gen_list_func(gen_mdtype=None):
    def_kwargs = {}
    def_kwargs.update(_eval_args)
    def_kwargs.update(_inheritance_args)
    def_kwargs.update(_global_args)
    def list_template(unbound=False, gen_mdtype=gen_mdtype, def_kwargs=def_kwargs, **kwargs):
        _do_update_kwargs(def_kwargs, kwargs)
        ret = "?." + _build_eval(**kwargs) + " list_" + gen_mdtype + 's' + _build_inheritance(**kwargs)
        if unbound:
            ret += '_unbound'
        return _clean_str(ret)
    return list_template

def _gen_read_func(gen_mdtype=None, gen_read_type=None):
    def_kwargs = {}
    def_kwargs.update(_eval_args)
    def_kwargs.update(_inheritance_args)
    def_kwargs.update(_global_args)
    def read_template(name=None, value=None,
            unbound=False, gen_mdtype=gen_mdtype, gen_read_type=gen_read_type,
            def_kwargs=def_kwargs, **kwargs):

        if gen_read_type not in ('get', 'has'):
            raise RuntimeError('unkown read function type ' + gen_read_type)
        if gen_mdtype == 'objective':
            if value is None:
                value = HSExp(exp='true')
            # Objectives are always unbound and string
            value.unbound = True
            value.string = True
        else:
            if value is not None:
                raise RuntimeError("Only specify a value for objectives")
        if gen_read_type == 'has' and unbound:
            raise RuntimeError('unbound only allowed on get, not on has')

        # XXX DFQ objective values should always be unbound, on setting? getting? both?

        _do_update_kwargs(def_kwargs, kwargs)
        ret = "?." + _build_eval(**kwargs) + " " + gen_read_type + "_" + gen_mdtype + _build_inheritance(**kwargs)
        if gen_read_type == 'get' and unbound:
            ret += '_unbound'
        ret += '('
        ret += '"' + name + '"'  # XXX DFQ, will an attribute/tag/etc name ever not be a string?
        if value is not None:
            if value.input_json is True:
                ret += ', EXPRESSION_FROM_JSON(' + str(value) + ')'
            else:
                ret += ', EXPRESSION_FROM_TEXT(' + str(value) + ')'
        ret += ')'
        return _clean_str(ret)
    return read_template

def _gen_update_func(gen_mdtype=None, gen_update_type=None, gen_table=None):
    def_kwargs = {}
    def_kwargs.update(_set_args)
    def_kwargs.update(_global_args)
    def update_template(name=None, value=HSExp(exp='true', string=True, input_json=False), unbound=False,
            gen_mdtype=gen_mdtype, gen_update_type=gen_update_type, gen_table=gen_table,
            def_kwargs=def_kwargs, **kwargs):

        if gen_update_type not in ('set', 'add'):
            raise RuntimeError('unkown update function type ' + gen_update_type)

        if not isinstance(value, HSExp):
            raise RuntimeError('value must be of type HSExp, passed in type ' + str(type(value)))

        _do_update_kwargs(def_kwargs, kwargs)

        if gen_update_type == 'add' and unbound:
            raise RuntimeError('unbound only allowed on set, not on add')

        # XXX DFQ objective values should always be unbound, on setting? getting? both?
        # XXX DFA Both

        ret = "?." + _build_set(**kwargs)

        if gen_mdtype == 'attribute':
            # annoying special case
            if value.input_json is True:
                ret += '_json'
            ret += ' ' + name + '=' + str(value)
        else:
            ret += ' #' + gen_table + '=' + gen_update_type + "_" + gen_mdtype
            ret += '('
            ret += '"' + name + '"'  # XXX DFQ, will an attribute/tag/etc name ever not be a string?
                                     # XXX DFA Yes it can be a string
            if gen_update_type == 'set' or gen_mdtype == 'objective':
                if unbound or gen_mdtype == 'objective':
                    value.unbound = True
                value.string = True
                if value.input_json is True:
                    ret += ', EXPRESSION_FROM_JSON(' + str(value) + ')'
                else:
                    ret += ', EXPRESSION_FROM_TEXT(' + str(value) + ')'
            ret += ')'
        return _clean_str(ret)
    return update_template

def _gen_del_func(gen_mdtype=None, gen_table=None):
    def_kwargs = {}
    def_kwargs.update(_set_args)
    def_kwargs.update(_global_args)
    def del_template(name=None, value=None,
            gen_mdtype=gen_mdtype, gen_table=gen_table,
            def_kwargs=def_kwargs, **kwargs):

        if gen_mdtype == 'objective' and value is None:
            value = HSExp(exp='true')

        if value is not None:
            if not isinstance(value, HSExp):
                raise RuntimeError('value must be of type HSExp or None, passed in type ' + str(type(value)))

        _do_update_kwargs(def_kwargs, kwargs)

        # XXX DFQ objective values should always be unbound, on setting? getting? both?
        # XXX DFA - on both
        ret = "?." + _build_set(**kwargs) + ' '

        if gen_mdtype == 'attribute':
            # annoying special case
            ret += name + '=' + '#EMPTY'
        else:
            if kwargs['force']:
                ret += '#' + gen_table + "=delete_force_" + gen_mdtype
            else:
                ret += '#' + gen_table + "=delete_" + gen_mdtype
            ret += '('
            ret += '"' + name + '"'  # XXX DFQ, will an attribute/tag/etc name ever not be a string?
                                     # XXX DFS Yes they can be strings
            if gen_mdtype == 'objective':
                value.unbound = True
                value.string = True
                if value.input_json is True:
                    ret += ', EXPRESSION_FROM_JSON(' + str(value) + ')'
                else:
                    ret += ', EXPRESSION_FROM_TEXT(' + str(value) + ')'
            ret += ')'
        return _clean_str(ret)
    return del_template


attribute_list = _gen_list_func('attribute')
attribute_get = _gen_read_func('attribute', 'get')
attribute_has = _gen_read_func('attribute', 'has')
attribute_set = _gen_update_func('attribute', 'set')
attribute_del = _gen_del_func('attribute')

tag_list = _gen_list_func('tag')
tag_get = _gen_read_func('tag', 'get')
tag_has = _gen_read_func('tag', 'has')
tag_set = _gen_update_func('tag', 'set', 'tags')
tag_del = _gen_del_func('tag', 'tags')

rekognition_tag_list = _gen_list_func('rekognition_tag')
rekognition_tag_get = _gen_read_func('rekognition_tag', 'get')
rekognition_tag_has = _gen_read_func('rekognition_tag', 'has')
rekognition_tag_set = _gen_update_func('rekognition_tag', 'set', 'rekognition_tags')
rekognition_tag_del = _gen_del_func('rekognition_tag', 'rekognition_tags')

label_list = _gen_list_func('label')
label_has = _gen_read_func('label', 'has')
label_add = _gen_update_func('label', 'add', 'assigned_labels')
label_del = _gen_del_func('label', 'assigned_labels')

keyword_list = _gen_list_func('keyword')
keyword_has = _gen_read_func('keyword', 'has')
keyword_add = _gen_update_func('keyword', 'add', 'keywords')
keyword_del = _gen_del_func('keyword', 'keywords')

objective_list = _gen_list_func('objective')
objective_has = _gen_read_func('objective', 'has')
objective_add = _gen_update_func('objective', 'add', 'objectives')
objective_del = _gen_del_func('objective', 'objectives')

def eval(value=None, **kwargs):
    def_kwargs = {}
    def_kwargs.update(_global_args)
    def_kwargs.update(_eval_args)
    _do_update_kwargs(def_kwargs, kwargs)

    if not isinstance(value, HSExp):
        raise RuntimeError('value must be of type HSExp, passed in type ' + str(type(value)))
    ret = "?." + _build_eval(**kwargs)
    if value.input_json is True:
        ret += " EVAL(EXPRESSION_FROM_JSON('" + str(value) + "'))"
    else:
        ret += " " + str(value) + ""
    return _clean_str(ret)

def sum(value=None, **kwargs):
    def_kwargs = {}
    def_kwargs.update(_global_args)
    def_kwargs.update(_sum_args)
    _do_update_kwargs(def_kwargs, kwargs)

    if not isinstance(value, HSExp):
        raise RuntimeError('value must be of type HSExp, passed in type ' + str(type(value)))
    ret = "?." + _build_sum(**kwargs);
    if value.input_json is True:
        ret += " EVAL(EXPRESSION_FROM_JSON('" + str(value) + "'))"
    else:
        ret += " " + str(value) + ""
    return _clean_str(ret)


###
### Simple Commands
###

def rm_rf(value=None, **kwargs):
    return _clean_str("?.rm-rf")

def cp_a(value=None, **kwargs):
    ret = "?.cp-a %d" % (kwargs['dest_inode'])
    return _clean_str(ret)

def inode_info(value=None, **kwargs):
    ret = "?.attribute=inode_info"
    return _clean_str(ret)

if __name__ == '__main__':
    print attribute_list()
    print attribute_list(inherited=True, recursive=True)

    print attribute_get('myattr')
    print attribute_has('myattr')
    print attribute_has('myattr', inherited=True)
    print objective_has('myobj')
    print objective_has('myobj', HSExp(exp='IF SIZE>33KB'))

    tfile = ['./tfile']
    print attribute_set('myattr')
    print attribute_set('myattr', HSExp(exp='attrvalue'))
    print attribute_set('myattr', HSExp(exp='attrvalue'), unbound=True, inherited=True, recursive=True)
    print tag_set('mytag', HSExp(exp='tagval'))
    print tag_set('mytag', HSExp(exp='tagval'))
    print rekognition_tag_set('mytag', HSExp(exp='tagval'))

    print attribute_del('myattr', recursive=True)
    print label_del('mylabel', recursive=True)
    print objective_del('myobj')
    print objective_del('myobj', HSExp(exp='IF SIZE>33KB'))

    print eval(HSExp('1+1'))
    print eval(HSExp('1/1'))
    print eval(HSExp('SUMS_TABLE{TYPE,{1FILE,space_used,size}}'))

