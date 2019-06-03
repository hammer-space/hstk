#!/bin/bash

if [ "$1" ] ; then
    TDIR="$1" ; shift
else
    TDIR=/mnt/hs/testshare
fi

mkdir -p $TDIR/dir1/dir2/dir3/dir4/dir5/dir6
for dn in $(find $TDIR -type d -print) ; do
    echo hello > $dn/file
done

set -u
#set -e
set -x

# TODO LIST:
#    Need to make -s/--string an alternative to -e not a modifier thereto
#    Fix escaping of embedded quotes
#    Need to add the <verb> <noun> aliases
#    Need to have set objective default to --unbound and need --bound as set



function test_attributes {
    # ATTRIBUTE RELATED
    hs attribute add color -e blue --string $TDIR/file
    hs attribute set color -e blue --string $TDIR/file
    hs attribute get color $TDIR/file
    hs attribute get --local color $TDIR/file
    hs attribute get --inherited color $TDIR/file
    hs attribute get --object color $TDIR/file
    hs attribute has color $TDIR/file
    hs attribute has --local color $TDIR/file
    hs attribute has --inherited color $TDIR/file
    hs attribute has --object color $TDIR/file
    hs attribute set color -e blue --string $TDIR/file
    # This next line is expected to fail
#    hs attribute set color -e "the color is \"blue" --string $TDIR/file
    hs attribute set color -e "the color is \'blue" --string $TDIR/file
    hs attribute set color -e green --string $TDIR/file
    hs attribute set color -e '#EMPTY' $TDIR/file
    hs attribute set color -e 'OLD_VALUE&"blue"' $TDIR/file
    hs attribute get color $TDIR/file
    hs attribute set color -e 'OLD_VALUE&"blue"' $TDIR/file
    hs attribute get color $TDIR/file
    hs attribute list $TDIR/file
    hs attribute list --local $TDIR/file
    hs attribute list --inherited $TDIR/file
    hs attribute list --object $TDIR/file
    hs attribute delete color $TDIR/
    hs attribute set color -e '#empty' $TDIR/
    hs attribute get color $TDIR/file

    # RECURSIVE ATTRIBUTE RELATED
    hs attribute set --recursive selected -e TRUE $TDIR/dir1
    hs attribute get selected $TDIR/dir1/file
    hs attribute get --recursive selected $TDIR/dir1
    hs attribute get --recursive --raw selected $TDIR/dir1
    hs attribute get --recursive --compact selected $TDIR/dir1
    hs attribute get --recursive --local selected $TDIR/dir1
    hs attribute get --recursive --local --raw selected $TDIR/dir1
    hs attribute get --recursive --local --compact selected $TDIR/dir1
    hs attribute get --recursive --inherited selected $TDIR/dir1
    hs attribute get --recursive --inherited --raw selected $TDIR/dir1
    hs attribute get --recursive --inherited --compact selected $TDIR/dir1
    hs attribute get --recursive --object selected $TDIR/dir1
    hs attribute get --recursive --object --raw selected $TDIR/dir1
    hs attribute get --recursive --object --compact selected $TDIR/dir1
    hs attribute get --recursive --unbound selected $TDIR/dir1
    hs attribute get --recursive --unbound --raw selected $TDIR/dir1
    hs attribute get --recursive --unbound --compact selected $TDIR/dir1
    hs attribute get --recursive --unbound --local selected $TDIR/dir1
    hs attribute get --recursive --unbound --local --raw selected $TDIR/dir1
    hs attribute get --recursive --unbound --local --compact selected $TDIR/dir1
    hs attribute get --recursive --unbound --inherited selected $TDIR/dir1
    hs attribute get --recursive --unbound --inherited --raw selected $TDIR/dir1
    hs attribute get --recursive --unbound --inherited --compact selected $TDIR/dir1
    hs attribute get --recursive --unbound --object selected $TDIR/dir1
    hs attribute get --recursive --unbound --object --raw selected $TDIR/dir1
    hs attribute get --recursive --unbound --object --compact selected $TDIR/dir1
    hs attribute has --recursive --raw selected $TDIR/dir1
    hs attribute has --recursive --compact selected $TDIR/dir1
    hs attribute has --recursive --local selected $TDIR/dir1
    hs attribute has --recursive --local --raw selected $TDIR/dir1
    hs attribute has --recursive --local --compact selected $TDIR/dir1
    hs attribute has --recursive --inherited selected $TDIR/dir1
    hs attribute has --recursive --inherited --raw selected $TDIR/dir1
    hs attribute has --recursive --inherited --compact selected $TDIR/dir1
    hs attribute has --recursive --object selected $TDIR/dir1
    hs attribute has --recursive --object --raw selected $TDIR/dir1
    hs attribute has --recursive --object --compact selected $TDIR/dir1
    hs attribute delete --recursive selected $TDIR/dir1
    hs attribute delete --recursive --force selected $TDIR/dir1
    hs attribute set --recursive selected -e '#empty' $TDIR/dir1
    hs attribute get selected $TDIR/dir1/file

    # CONTINUOUSLY EVALUATED FORMULA ATTRIBUTES
    hs attribute set selected -e 'EXPRESSION(SIZE>5bytes)' $TDIR/file
    hs attribute get selected $TDIR/file
    hs attribute set --unbound selected -e 'SIZE>5bytes' $TDIR/file
    hs attribute get --unbound selected $TDIR/file # cat $TDIR/file?.eval GET_ATTRIBUTE_UNBOUND("selected")
    hs attribute get selected $TDIR/file
    hs attribute get --raw selected $TDIR/file
    hs attribute get --compact selected $TDIR/file

    # ACCESSING ATTRIBUTES FROM WITHIN SCRIPT
    hs eval -e 'get_attribute("color")' $TDIR/file
    hs eval -e 'get_attribute_local("color")' $TDIR/file
    hs eval -e 'get_attribute_inherited("color")' $TDIR/file
    hs eval -e 'get_attribute_unbound("color")' $TDIR/file
    hs eval -e 'get_attribute_local_unbound("color")' $TDIR/file
    hs eval -e 'get_attribute_inherited_unbound("color")' $TDIR/file
    hs eval -e 'attributes.color' $TDIR/file
    hs eval -e 'attributes.color=="blue"' $TDIR/file
    hs eval -e 'list_attributes' $TDIR/file
    hs eval -e 'list_attributes_local' $TDIR/file
    hs eval -e 'list_attributes_inherited' $TDIR/file
}

function test_attributes_json {
    # ATTRIBUTE RELATED
    hs --json attribute add color -e blue --string $TDIR/file
    hs --json attribute set color -e blue --string $TDIR/file
    hs --json attribute get color $TDIR/file
    hs --json attribute get --local color $TDIR/file
    hs --json attribute get --inherited color $TDIR/file
    hs --json attribute get --object color $TDIR/file
    hs --json attribute has color $TDIR/file
    hs --json attribute has --local color $TDIR/file
    hs --json attribute has --inherited color $TDIR/file
    hs --json attribute has --object color $TDIR/file
    hs --json attribute set color -e blue --string $TDIR/file
    # This next line is expected to fail
#    hs --json attribute set color -e "the color is \"blue" --string $TDIR/file
    hs --json attribute set color -e "the color is \'blue" --string $TDIR/file
    hs --json attribute set color -e green --string $TDIR/file
    hs --json attribute set color -e '#EMPTY' $TDIR/file
    hs --json attribute set color -e 'OLD_VALUE&"blue"' $TDIR/file
    hs --json attribute get color $TDIR/file
    hs --json attribute set color -e 'OLD_VALUE&"blue"' $TDIR/file
    hs --json attribute get color $TDIR/file
    hs --json attribute list $TDIR/file
    hs --json attribute list --local $TDIR/file
    hs --json attribute list --inherited $TDIR/file
    hs --json attribute list --object $TDIR/file
    hs --json attribute delete color $TDIR/
    hs --json attribute set color -e '#empty' $TDIR/
    hs --json attribute get color $TDIR/file

    # RECURSIVE ATTRIBUTE RELATED
    hs --json attribute set --recursive selected -e TRUE $TDIR/dir1
    hs --json attribute get selected $TDIR/dir1/file
    hs --json attribute get --recursive selected $TDIR/dir1
    hs --json attribute get --recursive --raw selected $TDIR/dir1
    hs --json attribute get --recursive --compact selected $TDIR/dir1
    hs --json attribute get --recursive --local selected $TDIR/dir1
    hs --json attribute get --recursive --local --raw selected $TDIR/dir1
    hs --json attribute get --recursive --local --compact selected $TDIR/dir1
    hs --json attribute get --recursive --inherited selected $TDIR/dir1
    hs --json attribute get --recursive --inherited --raw selected $TDIR/dir1
    hs --json attribute get --recursive --inherited --compact selected $TDIR/dir1
    hs --json attribute get --recursive --object selected $TDIR/dir1
    hs --json attribute get --recursive --object --raw selected $TDIR/dir1
    hs --json attribute get --recursive --object --compact selected $TDIR/dir1
    hs --json attribute get --recursive --unbound selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --raw selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --compact selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --local selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --local --raw selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --local --compact selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --inherited selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --inherited --raw selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --inherited --compact selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --object selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --object --raw selected $TDIR/dir1
    hs --json attribute get --recursive --unbound --object --compact selected $TDIR/dir1
    hs --json attribute has --recursive --raw selected $TDIR/dir1
    hs --json attribute has --recursive --compact selected $TDIR/dir1
    hs --json attribute has --recursive --local selected $TDIR/dir1
    hs --json attribute has --recursive --local --raw selected $TDIR/dir1
    hs --json attribute has --recursive --local --compact selected $TDIR/dir1
    hs --json attribute has --recursive --inherited selected $TDIR/dir1
    hs --json attribute has --recursive --inherited --raw selected $TDIR/dir1
    hs --json attribute has --recursive --inherited --compact selected $TDIR/dir1
    hs --json attribute has --recursive --object selected $TDIR/dir1
    hs --json attribute has --recursive --object --raw selected $TDIR/dir1
    hs --json attribute has --recursive --object --compact selected $TDIR/dir1
    hs --json attribute delete --recursive selected $TDIR/dir1
    hs --json attribute delete --recursive --force selected $TDIR/dir1
    hs --json attribute set --recursive selected -e '#empty' $TDIR/dir1
    hs --json attribute get selected $TDIR/dir1/file

    # CONTINUOUSLY EVALUATED FORMULA ATTRIBUTES
    hs --json attribute set selected -e 'EXPRESSION(SIZE>5bytes)' $TDIR/file
    hs --json attribute get selected $TDIR/file
    hs --json attribute set --unbound selected -e 'SIZE>5bytes' $TDIR/file
    hs --json attribute get --unbound selected $TDIR/file # cat $TDIR/file?.eval GET_ATTRIBUTE_UNBOUND("selected")
    hs --json attribute get selected $TDIR/file
    hs --json attribute get --raw selected $TDIR/file
    hs --json attribute get --compact selected $TDIR/file

    # ACCESSING ATTRIBUTES FROM WITHIN SCRIPT
    hs --json eval -e 'get_attribute("color")' $TDIR/file
    hs --json eval -e 'get_attribute_local("color")' $TDIR/file
    hs --json eval -e 'get_attribute_inherited("color")' $TDIR/file
    hs --json eval -e 'get_attribute_unbound("color")' $TDIR/file
    hs --json eval -e 'get_attribute_local_unbound("color")' $TDIR/file
    hs --json eval -e 'get_attribute_inherited_unbound("color")' $TDIR/file
    hs --json eval -e 'attributes.color' $TDIR/file
    hs --json eval -e 'attributes.color=="blue"' $TDIR/file
    hs --json eval -e 'list_attributes' $TDIR/file
    hs --json eval -e 'list_attributes_local' $TDIR/file
    hs --json eval -e 'list_attributes_inherited' $TDIR/file
}

function test_tags {
    # TAG RELATED
    hs tag add mytag -e 1gbyte $TDIR/file  # Need to implement tag add
    hs tag get mytag $TDIR/file
    hs tag set mytag -e 1gbyte $TDIR/file
    hs tag get --local mytag $TDIR/file
    hs tag get --inherited mytag $TDIR/file
    hs tag get --object mytag $TDIR/file
    hs tag has mytag $TDIR/file
    hs tag has --local mytag $TDIR/file
    hs tag has --inherited mytag $TDIR/file
    hs tag has --object mytag $TDIR/file
    hs tag list $TDIR/file
    hs tag list --local $TDIR/file
    hs tag list --inherited $TDIR/file
    hs tag list --object $TDIR/file
    # This next line is expected to fail
#    hs tag delete mytag $TDIR/file
    hs tag delete --force mytag $TDIR/file
    hs tag get mytag $TDIR/file
    hs tag set mytag -e "'some string'" --string $TDIR/file
    hs tag get mytag $TDIR/file
    hs tag set mytag -e '#EMPTY' $TDIR/file
    hs tag get mytag $TDIR/file
    hs tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs tag get mytag $TDIR/file
    hs tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs tag get mytag $TDIR/file

    # RECURSIVE TAG RELATED
    hs tag add --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs tag set --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs tag get mytag $TDIR/dir1/file
    hs tag get --recursive mytag $TDIR/dir1/file
    hs tag get --recursive --raw mytag $TDIR/dir1/file
    hs tag get --recursive --compact mytag $TDIR/dir1/file
    hs tag get --recursive --local mytag $TDIR/dir1/file
    hs tag get --recursive --local --raw mytag $TDIR/dir1/file
    hs tag get --recursive --local --compact mytag $TDIR/dir1/file
    hs tag get --recursive --inherited mytag $TDIR/dir1/file
    hs tag get --recursive --inherited --raw mytag $TDIR/dir1/file
    hs tag get --recursive --inherited --compact mytag $TDIR/dir1/file
    hs tag get --recursive --object mytag $TDIR/dir1/file
    hs tag get --recursive --object --raw mytag $TDIR/dir1/file
    hs tag get --recursive --object --compact mytag $TDIR/dir1/file
    hs tag get --recursive --unbound mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --raw mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --compact mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --local mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --local --raw mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --local --compact mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --inherited mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --inherited --raw mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --inherited --compact mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --object mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --object --raw mytag $TDIR/dir1/file
    hs tag get --recursive --unbound --object --compact mytag $TDIR/dir1/file
    hs tag has --recursive mytag $TDIR/dir1/file
    hs tag has --recursive --raw mytag $TDIR/dir1/file
    hs tag has --recursive --compact mytag $TDIR/dir1/file
    hs tag has --recursive --local mytag $TDIR/dir1/file
    hs tag has --recursive --local --raw mytag $TDIR/dir1/file
    hs tag has --recursive --local --compact mytag $TDIR/dir1/file
    hs tag has --recursive --inherited mytag $TDIR/dir1/file
    hs tag has --recursive --inherited --raw mytag $TDIR/dir1/file
    hs tag has --recursive --inherited --compact mytag $TDIR/dir1/file
    hs tag has --recursive --object mytag $TDIR/dir1/file
    hs tag has --recursive --object --raw mytag $TDIR/dir1/file
    hs tag has --recursive --object --compact mytag $TDIR/dir1/file

    hs tag delete --recursive mytag $TDIR/dir1
    hs tag delete --recursive --force mytag $TDIR/dir1
    hs tag get mytag $TDIR/dir1/file

    # CONTINUOUSLY EVALUATED FORMULA TAGS
    hs tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs tag get mytag $TDIR/dir1
    hs tag set --unbound mytag -e 'NOW' $TDIR/dir1
    hs tag get --unbound mytag $TDIR/dir1 # cat $TDIR/file?.eval GET_TAG_UNBOUND("mytag")
    hs tag get mytag $TDIR/dir1
    sleep 2
    hs tag get mytag $TDIR/dir1
    hs tag get --raw mytag $TDIR/dir1
    hs tag get --compact mytag $TDIR/dir1
    hs tag delete mytag $TDIR/dir1
    hs tag delete --force mytag $TDIR/dir1

    # FROM WITHIN A SCRIPT
    # XXX hs eval 'set_tag("mytag", "1gbyte")' $TDIR/file
    hs tag set mytag -e 1gbyte $TDIR/file
    # hs eval -e 'get_tag("mytag")==1gbyte' $TDIR/file
    # THIS ONE IS EXPECTED TO RETURN AN ERROR    hs eval -e 'get_tag("mytag")=="1gbyte"' $TDIR/file
    hs eval -e 'get_tag("mytag")' $TDIR/file
    hs tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs eval -e 'get_tag("mytag")' $TDIR/file
    hs eval -e 'get_tag_local("mytag")' $TDIR/file
    hs eval -e 'get_tag_inherited("mytag")' $TDIR/file
    hs eval -e 'get_tag_unbound("mytag")' $TDIR/file
    hs eval -e 'get_tag_local_unbound("mytag")' $TDIR/file
    hs eval -e 'get_tag_inherited_unbound("mytag")' $TDIR/file
    hs eval -e 'has_tag("mytag")' $TDIR/file
    hs eval -e 'has_tag_local("mytag")' $TDIR/file
    hs eval -e 'has_tag_inherited("mytag")' $TDIR/file
    hs eval -e 'list_tags' $TDIR/file
    hs eval -e 'list_tags_local' $TDIR/file
    hs eval -e 'list_tags_inherited' $TDIR/file
    hs eval -e 'attributes.#TAGS' $TDIR/file
}

function test_tags_json {
    # TAG RELATED
    hs --json tag add mytag -e 1gbyte $TDIR/file  # Need to implement tag add
    hs --json tag get mytag $TDIR/file
    hs --json tag set mytag -e 1gbyte $TDIR/file
    hs --json tag get --local mytag $TDIR/file
    hs --json tag get --inherited mytag $TDIR/file
    hs --json tag get --object mytag $TDIR/file
    hs --json tag has mytag $TDIR/file
    hs --json tag has --local mytag $TDIR/file
    hs --json tag has --inherited mytag $TDIR/file
    hs --json tag has --object mytag $TDIR/file
    hs --json tag list $TDIR/file
    hs --json tag list --local $TDIR/file
    hs --json tag list --inherited $TDIR/file
    hs --json tag list --object $TDIR/file
    # This next line is expected to fail
#    hs --json tag delete mytag $TDIR/file
    hs --json tag delete --force mytag $TDIR/file
    hs --json tag get mytag $TDIR/file
    hs --json tag set mytag -e "'some string'" --string $TDIR/file
    hs --json tag get mytag $TDIR/file
    hs --json tag set mytag -e '#EMPTY' $TDIR/file
    hs --json tag get mytag $TDIR/file
    hs --json tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs --json tag get mytag $TDIR/file
    hs --json tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs --json tag get mytag $TDIR/file

    # RECURSIVE TAG RELATED
    hs --json tag add --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json tag set --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json tag get mytag $TDIR/dir1/file
    hs --json tag get --recursive mytag $TDIR/dir1/file
    hs --json tag get --recursive --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --compact mytag $TDIR/dir1/file
    hs --json tag get --recursive --local mytag $TDIR/dir1/file
    hs --json tag get --recursive --local --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --local --compact mytag $TDIR/dir1/file
    hs --json tag get --recursive --inherited mytag $TDIR/dir1/file
    hs --json tag get --recursive --inherited --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --inherited --compact mytag $TDIR/dir1/file
    hs --json tag get --recursive --object mytag $TDIR/dir1/file
    hs --json tag get --recursive --object --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --object --compact mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --compact mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --local mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --local --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --local --compact mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --inherited mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --inherited --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --inherited --compact mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --object mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --object --raw mytag $TDIR/dir1/file
    hs --json tag get --recursive --unbound --object --compact mytag $TDIR/dir1/file
    hs --json tag has --recursive mytag $TDIR/dir1/file
    hs --json tag has --recursive --raw mytag $TDIR/dir1/file
    hs --json tag has --recursive --compact mytag $TDIR/dir1/file
    hs --json tag has --recursive --local mytag $TDIR/dir1/file
    hs --json tag has --recursive --local --raw mytag $TDIR/dir1/file
    hs --json tag has --recursive --local --compact mytag $TDIR/dir1/file
    hs --json tag has --recursive --inherited mytag $TDIR/dir1/file
    hs --json tag has --recursive --inherited --raw mytag $TDIR/dir1/file
    hs --json tag has --recursive --inherited --compact mytag $TDIR/dir1/file
    hs --json tag has --recursive --object mytag $TDIR/dir1/file
    hs --json tag has --recursive --object --raw mytag $TDIR/dir1/file
    hs --json tag has --recursive --object --compact mytag $TDIR/dir1/file

    hs --json tag delete --recursive mytag $TDIR/dir1
    hs --json tag delete --recursive --force mytag $TDIR/dir1
    hs --json tag get mytag $TDIR/dir1/file

    # CONTINUOUSLY EVALUATED FORMULA TAGS
    hs --json tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json tag get mytag $TDIR/dir1
    hs --json tag set --unbound mytag -e 'NOW' $TDIR/dir1
    hs --json tag get --unbound mytag $TDIR/dir1 # cat $TDIR/file?.eval GET_TAG_UNBOUND("mytag")
    hs --json tag get mytag $TDIR/dir1
    sleep 2
    hs --json tag get mytag $TDIR/dir1
    hs --json tag get --raw mytag $TDIR/dir1
    hs --json tag get --compact mytag $TDIR/dir1
    hs --json tag delete mytag $TDIR/dir1
    hs --json tag delete --force mytag $TDIR/dir1

    # FROM WITHIN A SCRIPT
    # XXX hs --json eval 'set_tag("mytag", "1gbyte")' $TDIR/file
    hs --json tag set mytag -e 1gbyte $TDIR/file
    # hs --json eval -e 'get_tag("mytag")==1gbyte' $TDIR/file
    # THIS ONE IS EXPECTED TO RETURN AN ERROR    hs --json eval -e 'get_tag("mytag")=="1gbyte"' $TDIR/file
    hs --json eval -e 'get_tag("mytag")' $TDIR/file
    hs --json tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json eval -e 'get_tag("mytag")' $TDIR/file
    hs --json eval -e 'get_tag_local("mytag")' $TDIR/file
    hs --json eval -e 'get_tag_inherited("mytag")' $TDIR/file
    hs --json eval -e 'get_tag_unbound("mytag")' $TDIR/file
    hs --json eval -e 'get_tag_local_unbound("mytag")' $TDIR/file
    hs --json eval -e 'get_tag_inherited_unbound("mytag")' $TDIR/file
    hs --json eval -e 'has_tag("mytag")' $TDIR/file
    hs --json eval -e 'has_tag_local("mytag")' $TDIR/file
    hs --json eval -e 'has_tag_inherited("mytag")' $TDIR/file
    hs --json eval -e 'list_tags' $TDIR/file
    hs --json eval -e 'list_tags_local' $TDIR/file
    hs --json eval -e 'list_tags_inherited' $TDIR/file
    hs --json eval -e 'attributes.#TAGS' $TDIR/file
}

function test_rekognition_tags {
    # TAG RELATED
    hs rekognition_tag add mytag -e 1gbyte $TDIR/file  # Need to implement tag add
    hs rekognition_tag get mytag $TDIR/file
    hs rekognition_tag set mytag -e "80%" $TDIR/file
    hs rekognition_tag get --local mytag $TDIR/file
    hs rekognition_tag get --inherited mytag $TDIR/file
    hs rekognition_tag get --object mytag $TDIR/file
    hs rekognition_tag has mytag $TDIR/file
    hs rekognition_tag has --local mytag $TDIR/file
    hs rekognition_tag has --inherited mytag $TDIR/file
    hs rekognition_tag has --object mytag $TDIR/file
    hs rekognition_tag list $TDIR/file
    hs rekognition_tag list --local $TDIR/file
    hs rekognition_tag list --inherited $TDIR/file
    hs rekognition_tag list --object $TDIR/file
    # This next line is expected to fail
#    hs rekognition_tag delete mytag $TDIR/file
    hs rekognition_tag delete --force mytag $TDIR/file
    hs rekognition_tag get mytag $TDIR/file
    hs rekognition_tag set mytag -e "'some string'" --string $TDIR/file
    hs rekognition_tag get mytag $TDIR/file
    hs rekognition_tag set mytag -e '#EMPTY' $TDIR/file
    hs rekognition_tag get mytag $TDIR/file
    hs rekognition_tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs rekognition_tag get mytag $TDIR/file
    hs rekognition_tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs rekognition_tag get mytag $TDIR/file

    # RECURSIVE TAG RELATED
    hs rekognition_tag add --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs rekognition_tag set --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs rekognition_tag get mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --compact mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --local mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --local --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --local --compact mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --inherited mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --inherited --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --inherited --compact mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --object mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --object --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --object --compact mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --compact mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --local mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --local --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --local --compact mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --inherited mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --inherited --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --inherited --compact mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --object mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --object --raw mytag $TDIR/dir1/file
    hs rekognition_tag get --recursive --unbound --object --compact mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --raw mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --compact mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --local mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --local --raw mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --local --compact mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --inherited mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --inherited --raw mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --inherited --compact mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --object mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --object --raw mytag $TDIR/dir1/file
    hs rekognition_tag has --recursive --object --compact mytag $TDIR/dir1/file

    hs rekognition_tag delete --recursive mytag $TDIR/dir1
    hs rekognition_tag delete --recursive --force mytag $TDIR/dir1
    hs rekognition_tag get mytag $TDIR/dir1/file

    # CONTINUOUSLY EVALUATED FORMULA TAGS
    hs rekognition_tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs rekognition_tag get mytag $TDIR/dir1
    hs rekognition_tag set --unbound mytag -e 'NOW' $TDIR/dir1
    hs rekognition_tag get --unbound mytag $TDIR/dir1 # cat $TDIR/file?.eval GET_REKOGNITION_TAG_UNBOUND("mytag")
    hs rekognition_tag get mytag $TDIR/dir1
    sleep 2
    hs rekognition_tag get mytag $TDIR/dir1
    hs rekognition_tag get --raw mytag $TDIR/dir1
    hs rekognition_tag get --compact mytag $TDIR/dir1
    hs rekognition_tag delete mytag $TDIR/dir1
    hs rekognition_tag delete --force mytag $TDIR/dir1

    # FROM WITHIN A SCRIPT
    # XXX hs eval 'set_rekognition_tag("mytag", "1gbyte")' $TDIR/file
    hs rekognition_tag set mytag -e 1gbyte $TDIR/file
    # hs eval -e 'get_rekognition_tag("mytag")==1gbyte' $TDIR/file
    # THIS ONE IS EXPECTED TO RETURN AN ERROR    hs eval -e 'get_rekognition_tag("mytag")=="1gbyte"' $TDIR/file
    hs eval -e 'get_rekognition_tag("mytag")' $TDIR/file
    hs rekognition_tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs eval -e 'get_rekognition_tag("mytag")' $TDIR/file
    hs eval -e 'get_rekognition_tag_local("mytag")' $TDIR/file
    hs eval -e 'get_rekognition_tag_inherited("mytag")' $TDIR/file
    hs eval -e 'get_rekognition_tag_unbound("mytag")' $TDIR/file
    hs eval -e 'get_rekognition_tag_local_unbound("mytag")' $TDIR/file
    hs eval -e 'get_rekognition_tag_inherited_unbound("mytag")' $TDIR/file
    hs eval -e 'has_rekognition_tag("mytag")' $TDIR/file
    hs eval -e 'has_rekognition_tag_local("mytag")' $TDIR/file
    hs eval -e 'has_rekognition_tag_inherited("mytag")' $TDIR/file
    hs eval -e 'list_rekognition_tags' $TDIR/file
    hs eval -e 'list_rekognition_tags_local' $TDIR/file
    hs eval -e 'list_rekognition_tags_inherited' $TDIR/file
    hs eval -e 'attributes.#TAGS' $TDIR/file
    hs rekognition_tag delete mytag $TDIR/file
}

function test_rekognition_tags_json {
    # TAG RELATED
    hs --json rekognition_tag add mytag -e 1gbyte $TDIR/file  # Need to implement tag add
    hs --json rekognition_tag get mytag $TDIR/file
    hs --json rekognition_tag set mytag -e "80%" $TDIR/file
    hs --json rekognition_tag get --local mytag $TDIR/file
    hs --json rekognition_tag get --inherited mytag $TDIR/file
    hs --json rekognition_tag get --object mytag $TDIR/file
    hs --json rekognition_tag has mytag $TDIR/file
    hs --json rekognition_tag has --local mytag $TDIR/file
    hs --json rekognition_tag has --inherited mytag $TDIR/file
    hs --json rekognition_tag has --object mytag $TDIR/file
    hs --json rekognition_tag list $TDIR/file
    hs --json rekognition_tag list --local $TDIR/file
    hs --json rekognition_tag list --inherited $TDIR/file
    hs --json rekognition_tag list --object $TDIR/file
    # This next line is expected to fail
#    hs --json rekognition_tag delete mytag $TDIR/file
    hs --json rekognition_tag delete --force mytag $TDIR/file
    hs --json rekognition_tag get mytag $TDIR/file
    hs --json rekognition_tag set mytag -e "'some string'" --string $TDIR/file
    hs --json rekognition_tag get mytag $TDIR/file
    hs --json rekognition_tag set mytag -e '#EMPTY' $TDIR/file
    hs --json rekognition_tag get mytag $TDIR/file
    hs --json rekognition_tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs --json rekognition_tag get mytag $TDIR/file
    hs --json rekognition_tag set mytag -e 'OLD_VALUE+1' $TDIR/file
    hs --json rekognition_tag get mytag $TDIR/file

    # RECURSIVE TAG RELATED
    hs --json rekognition_tag add --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json rekognition_tag set --recursive mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json rekognition_tag get mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --local mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --local --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --local --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --inherited mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --inherited --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --inherited --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --object mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --object --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --object --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --local mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --local --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --local --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --inherited mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --inherited --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --inherited --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --object mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --object --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag get --recursive --unbound --object --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --local mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --local --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --local --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --inherited mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --inherited --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --inherited --compact mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --object mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --object --raw mytag $TDIR/dir1/file
    hs --json rekognition_tag has --recursive --object --compact mytag $TDIR/dir1/file

    hs --json rekognition_tag delete --recursive mytag $TDIR/dir1
    hs --json rekognition_tag delete --recursive --force mytag $TDIR/dir1
    hs --json rekognition_tag get mytag $TDIR/dir1/file

    # CONTINUOUSLY EVALUATED FORMULA TAGS
    hs --json rekognition_tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json rekognition_tag get mytag $TDIR/dir1
    hs --json rekognition_tag set --unbound mytag -e 'NOW' $TDIR/dir1
    hs --json rekognition_tag get --unbound mytag $TDIR/dir1 # cat $TDIR/file?.eval GET_REKOGNITION_TAG_UNBOUND("mytag")
    hs --json rekognition_tag get mytag $TDIR/dir1
    sleep 2
    hs --json rekognition_tag get mytag $TDIR/dir1
    hs --json rekognition_tag get --raw mytag $TDIR/dir1
    hs --json rekognition_tag get --compact mytag $TDIR/dir1
    hs --json rekognition_tag delete mytag $TDIR/dir1
    hs --json rekognition_tag delete --force mytag $TDIR/dir1

    # FROM WITHIN A SCRIPT
    # XXX hs --json eval 'set_rekognition_tag("mytag", "1gbyte")' $TDIR/file
    hs --json rekognition_tag set mytag -e 1gbyte $TDIR/file
    # hs --json eval -e 'get_rekognition_tag("mytag")==1gbyte' $TDIR/file
    # THIS ONE IS EXPECTED TO RETURN AN ERROR    hs --json eval -e 'get_rekognition_tag("mytag")=="1gbyte"' $TDIR/file
    hs --json eval -e 'get_rekognition_tag("mytag")' $TDIR/file
    hs --json rekognition_tag set mytag -e 'EXPRESSION(NOW)' $TDIR/dir1
    hs --json eval -e 'get_rekognition_tag("mytag")' $TDIR/file
    hs --json eval -e 'get_rekognition_tag_local("mytag")' $TDIR/file
    hs --json eval -e 'get_rekognition_tag_inherited("mytag")' $TDIR/file
    hs --json eval -e 'get_rekognition_tag_unbound("mytag")' $TDIR/file
    hs --json eval -e 'get_rekognition_tag_local_unbound("mytag")' $TDIR/file
    hs --json eval -e 'get_rekognition_tag_inherited_unbound("mytag")' $TDIR/file
    hs --json eval -e 'has_rekognition_tag("mytag")' $TDIR/file
    hs --json eval -e 'has_rekognition_tag_local("mytag")' $TDIR/file
    hs --json eval -e 'has_rekognition_tag_inherited("mytag")' $TDIR/file
    hs --json eval -e 'list_rekognition_tags' $TDIR/file
    hs --json eval -e 'list_rekognition_tags_local' $TDIR/file
    hs --json eval -e 'list_rekognition_tags_inherited' $TDIR/file
    hs --json eval -e 'attributes.#TAGS' $TDIR/file
    hs --json rekognition_tag delete mytag $TDIR/file
}

function test_keywords {
    # KEYWORD RELATED
    hs keyword has mykeyword $TDIR/file
    hs keyword add mykeyword $TDIR/file
    hs keyword has mykeyword $TDIR/file
    hs keyword has --local mykeyword $TDIR/file
    hs keyword has --inherited mykeyword $TDIR/file
    hs keyword has --object mykeyword $TDIR/file
    hs keyword list $TDIR/file
    hs keyword list --local $TDIR/file
    hs keyword list --inherited $TDIR/file
    hs keyword list --object $TDIR/file
    # This next line is expected to fail
#    hs keyword delete mykeyword $TDIR/file
    hs keyword delete --force mykeyword $TDIR/file
    hs keyword has mykeyword $TDIR/file

    # RECURSIVE KEYWORD RELATED
    hs keyword has mykeyword $TDIR/dir1/file
    hs keyword add --recursive mykeyword $TDIR/dir1
    hs keyword has mykeyword $TDIR/dir1/file
    hs keyword has --recursive mykeyword $TDIR/dir1/file
    hs keyword has --recursive --raw mykeyword $TDIR/dir1/file
    hs keyword has --recursive --compact mykeyword $TDIR/dir1/file
    hs keyword has --recursive --local mykeyword $TDIR/dir1/file
    hs keyword has --recursive --local --raw mykeyword $TDIR/dir1/file
    hs keyword has --recursive --local --compact mykeyword $TDIR/dir1/file
    hs keyword has --recursive --inherited mykeyword $TDIR/dir1/file
    hs keyword has --recursive --inherited --raw mykeyword $TDIR/dir1/file
    hs keyword has --recursive --inherited --compact mykeyword $TDIR/dir1/file
    hs keyword has --recursive --object mykeyword $TDIR/dir1/file
    hs keyword has --recursive --object --raw mykeyword $TDIR/dir1/file
    hs keyword has --recursive --object --compact mykeyword $TDIR/dir1/file
    hs keyword delete --recursive mykeyword $TDIR/dir1
    hs keyword delete --recursive --force mykeyword $TDIR/dir1
    hs keyword has mykeyword $TDIR/dir1/file
    hs keyword has --raw mykeyword $TDIR/dir1/file # XXX Exists?
    hs keyword has --compact mykeyword $TDIR/dir1/file # XXX Exists?

    # KEYWORD FROM WITHIN A SCRIPT
    hs keyword add mykeyword $TDIR/file
    hs eval -e 'has_keyword("mykeyword")' $TDIR/file
    hs eval -e 'has_keyword_local("mykeyword")' $TDIR/file
    hs eval -e 'has_keyword_inherited("mykeyword")' $TDIR/file
    hs eval -e 'list_keywords' $TDIR/file
    hs eval -e 'list_keywords_local' $TDIR/file
    hs eval -e 'list_keywords_inherited' $TDIR/file
    hs keyword delete mykeyword $TDIR/file
    hs keyword delete --force mykeyword $TDIR/file
}

function test_keywords_json {
    # KEYWORD RELATED
    hs --json keyword has mykeyword $TDIR/file
    hs --json keyword add mykeyword $TDIR/file
    hs --json keyword has mykeyword $TDIR/file
    hs --json keyword has --local mykeyword $TDIR/file
    hs --json keyword has --inherited mykeyword $TDIR/file
    hs --json keyword has --object mykeyword $TDIR/file
    hs --json keyword list $TDIR/file
    hs --json keyword list --local $TDIR/file
    hs --json keyword list --inherited $TDIR/file
    hs --json keyword list --object $TDIR/file
    # This next line is expected to fail
#    hs --json keyword delete mykeyword $TDIR/file
    hs --json keyword delete --force mykeyword $TDIR/file
    hs --json keyword has mykeyword $TDIR/file

    # RECURSIVE KEYWORD RELATED
    hs --json keyword has mykeyword $TDIR/dir1/file
    hs --json keyword add --recursive mykeyword $TDIR/dir1
    hs --json keyword has mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --raw mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --compact mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --local mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --local --raw mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --local --compact mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --inherited mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --inherited --raw mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --inherited --compact mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --object mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --object --raw mykeyword $TDIR/dir1/file
    hs --json keyword has --recursive --object --compact mykeyword $TDIR/dir1/file
    hs --json keyword delete --recursive mykeyword $TDIR/dir1
    hs --json keyword delete --recursive --force mykeyword $TDIR/dir1
    hs --json keyword has mykeyword $TDIR/dir1/file
    hs --json keyword has --raw mykeyword $TDIR/dir1/file # XXX Exists?
    hs --json keyword has --compact mykeyword $TDIR/dir1/file # XXX Exists?

    # KEYWORD FROM WITHIN A SCRIPT
    hs --json keyword add mykeyword $TDIR/file
    hs --json eval -e 'has_keyword("mykeyword")' $TDIR/file
    hs --json eval -e 'has_keyword_local("mykeyword")' $TDIR/file
    hs --json eval -e 'has_keyword_inherited("mykeyword")' $TDIR/file
    hs --json eval -e 'list_keywords' $TDIR/file
    hs --json eval -e 'list_keywords_local' $TDIR/file
    hs --json eval -e 'list_keywords_inherited' $TDIR/file
    hs --json keyword delete mykeyword $TDIR/file
    hs --json keyword delete --force mykeyword $TDIR/file
}

function test_labels {
    # LABEL RELATED
    hs label has cat $TDIR/file
    hs label add cat $TDIR/file
    hs label has cat $TDIR/file
    hs label has --local cat $TDIR/file
    hs label has --inherited cat $TDIR/file
    hs label has --object cat $TDIR/file
    hs label delete cat $TDIR/file
    hs label delete cat --force $TDIR/file
    hs label has cat $TDIR/file
    hs label add cat $TDIR/file
    hs label list $TDIR/file
    hs label list --local $TDIR/file
    hs label list --inherited $TDIR/file
    hs label list --object $TDIR/file
    hs label delete cat $TDIR/file
    hs label delete cat --force $TDIR/file

    # RECURSIVE LABEL RELATED
    hs label add --recursive cat $TDIR/dir1
    hs label has cat $TDIR/dir1/file
    hs label has --recursive cat $TDIR/dir1/file
    hs label has --recursive --raw cat $TDIR/dir1/file
    hs label has --recursive --compact cat $TDIR/dir1/file
    hs label has --recursive --local cat $TDIR/dir1/file
    hs label has --recursive --local --raw cat $TDIR/dir1/file
    hs label has --recursive --local --compact cat $TDIR/dir1/file
    hs label has --recursive --inherited cat $TDIR/dir1/file
    hs label has --recursive --inherited --raw cat $TDIR/dir1/file
    hs label has --recursive --inherited --compact cat $TDIR/dir1/file
    hs label has --recursive --object cat $TDIR/dir1/file
    hs label has --recursive --object --raw cat $TDIR/dir1/file
    hs label has --recursive --object --compact cat $TDIR/dir1/file
    hs label delete --recursive cat $TDIR/dir1
    hs label delete --recursive --force cat $TDIR/dir1
    hs label has --raw cat $TDIR/dir1/file
    hs label has --compact cat $TDIR/dir1/file

    # LABEL FROM WITHIN A SCRIPT
    hs eval -e 'has_label("cat")' $TDIR/file
    hs eval -e 'has_label_local("cat")' $TDIR/file
    hs eval -e 'has_label_inherited("cat")' $TDIR/file
    hs label add cat $TDIR/file
    hs eval -e 'has_label("cat")' $TDIR/file  # XXX next few need more verification
    hs eval -e 'has_label("living thing")' $TDIR/file
    hs eval -e 'list_labels' $TDIR/file
    hs eval -e 'list_labels_local' $TDIR/file
    hs eval -e 'list_labels_inherited' $TDIR/file
    hs label delete cat $TDIR/file
    hs label delete cat --force $TDIR/file
}

function test_labels_json {
    # LABEL RELATED
    hs --json label has cat $TDIR/file
    hs --json label add cat $TDIR/file
    hs --json label has cat $TDIR/file
    hs --json label has --local cat $TDIR/file
    hs --json label has --inherited cat $TDIR/file
    hs --json label has --object cat $TDIR/file
    hs --json label delete cat $TDIR/file
    hs --json label delete cat --force $TDIR/file
    hs --json label has cat $TDIR/file
    hs --json label add cat $TDIR/file
    hs --json label list $TDIR/file
    hs --json label list --local $TDIR/file
    hs --json label list --inherited $TDIR/file
    hs --json label list --object $TDIR/file
    hs --json label delete cat $TDIR/file
    hs --json label delete cat --force $TDIR/file

    # RECURSIVE LABEL RELATED
    hs --json label add --recursive cat $TDIR/dir1
    hs --json label has cat $TDIR/dir1/file
    hs --json label has --recursive cat $TDIR/dir1/file
    hs --json label has --recursive --raw cat $TDIR/dir1/file
    hs --json label has --recursive --compact cat $TDIR/dir1/file
    hs --json label has --recursive --local cat $TDIR/dir1/file
    hs --json label has --recursive --local --raw cat $TDIR/dir1/file
    hs --json label has --recursive --local --compact cat $TDIR/dir1/file
    hs --json label has --recursive --inherited cat $TDIR/dir1/file
    hs --json label has --recursive --inherited --raw cat $TDIR/dir1/file
    hs --json label has --recursive --inherited --compact cat $TDIR/dir1/file
    hs --json label has --recursive --object cat $TDIR/dir1/file
    hs --json label has --recursive --object --raw cat $TDIR/dir1/file
    hs --json label has --recursive --object --compact cat $TDIR/dir1/file
    hs --json label delete --recursive cat $TDIR/dir1
    hs --json label delete --recursive --force cat $TDIR/dir1
    hs --json label has --raw cat $TDIR/dir1/file
    hs --json label has --compact cat $TDIR/dir1/file

    # LABEL FROM WITHIN A SCRIPT
    hs --json eval -e 'has_label("cat")' $TDIR/file
    hs --json eval -e 'has_label_local("cat")' $TDIR/file
    hs --json eval -e 'has_label_inherited("cat")' $TDIR/file
    hs --json label add cat $TDIR/file
    hs --json eval -e 'has_label("cat")' $TDIR/file  # XXX next few need more verification
    hs --json eval -e 'has_label("living thing")' $TDIR/file
    hs --json eval -e 'list_labels' $TDIR/file
    hs --json eval -e 'list_labels_local' $TDIR/file
    hs --json eval -e 'list_labels_inherited' $TDIR/file
    hs --json label delete cat $TDIR/file
    hs --json label delete cat --force $TDIR/file
}

function test_objectives {
    # OBJECTIVE RELATED 
    # following should default to equivalent of -e true
    hs objective add do-not-move $TDIR/file
    hs objective add do-not-move -e true $TDIR/file
    hs objective has do-not-move -e true $TDIR/file
    hs objective has --local do-not-move -e true $TDIR/file
    hs objective has --inherited do-not-move -e true $TDIR/file
    hs objective has --effective do-not-move -e true $TDIR/file
    hs objective has --active do-not-move -e true $TDIR/file
    hs objective has --share do-not-move -e true $TDIR/file
    hs objective has do-not-move $TDIR/file
    hs objective list $TDIR/file
    hs objective list --local $TDIR/file
    hs objective list --inherited $TDIR/file
    hs objective list --effective $TDIR/file
    hs objective list --active $TDIR/file
    hs objective list --share $TDIR/file
    hs objective delete do-not-move -e true $TDIR/file
    hs objective delete --force do-not-move -e true $TDIR/file
    # This next line is expected to fail
#    hs objective delete do-not-move $TDIR/file
    hs objective add "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/file
    hs objective has "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/file
    hs objective add "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs objective has "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs objective add "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/file
    hs objective delete "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs objective delete --force "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs objective has "Place-on-Node11.rw.net"  $TDIR/file
    hs objective has do-not-move $TDIR/file
    # RECURSIVE OBJECTIVE RELATED
    hs objective add --recursive "do-not-move" -e true $TDIR/
    hs objective has --recursive "do-not-move" -e true $TDIR/
    hs objective has --recursive --raw "do-not-move" -e true $TDIR/
    hs objective has --recursive --compact "do-not-move" -e true $TDIR/
    hs objective has --recursive --local "do-not-move" -e true $TDIR/
    hs objective has --recursive --local --raw "do-not-move" -e true $TDIR/
    hs objective has --recursive --local --compact "do-not-move" -e true $TDIR/
    hs objective has --recursive --inherited "do-not-move" -e true $TDIR/
    hs objective has --recursive --inherited --raw "do-not-move" -e true $TDIR/
    hs objective has --recursive --inherited --compact "do-not-move" -e true $TDIR/
    hs objective has --recursive --effective "do-not-move" -e true $TDIR/
    hs objective has --recursive --effective --raw "do-not-move" -e true $TDIR/
    hs objective has --recursive --effective --compact "do-not-move" -e true $TDIR/
    hs objective has --recursive --active "do-not-move" -e true $TDIR/
    hs objective has --recursive --active --raw "do-not-move" -e true $TDIR/
    hs objective has --recursive --active --compact "do-not-move" -e true $TDIR/
    hs objective has --recursive --share "do-not-move" -e true $TDIR/
    hs objective has --recursive --share --raw "do-not-move" -e true $TDIR/
    hs objective has --recursive --share --compact "do-not-move" -e true $TDIR/
    hs objective delete --recursive "do-not-move" -e true $TDIR/
    hs objective delete --recursive --force "do-not-move" -e true $TDIR/
    hs objective add --recursive "do-not-move" $TDIR/ # implied -e true
    hs objective delete --recursive "do-not-move" $TDIR/
    hs objective add --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/
    hs objective add --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/
    hs objective delete --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/
    hs objective delete --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/
}

function test_objectives_json {
    # OBJECTIVE RELATED 
    # following should default to equivalent of -e true
    hs --json objective add do-not-move $TDIR/file
    hs --json objective add do-not-move -e true $TDIR/file
    hs --json objective has do-not-move -e true $TDIR/file
    hs --json objective has --local do-not-move -e true $TDIR/file
    hs --json objective has --inherited do-not-move -e true $TDIR/file
    hs --json objective has --effective do-not-move -e true $TDIR/file
    hs --json objective has --active do-not-move -e true $TDIR/file
    hs --json objective has --share do-not-move -e true $TDIR/file
    hs --json objective has do-not-move $TDIR/file
    hs --json objective list $TDIR/file
    hs --json objective list --local $TDIR/file
    hs --json objective list --inherited $TDIR/file
    hs --json objective list --effective $TDIR/file
    hs --json objective list --active $TDIR/file
    hs --json objective list --share $TDIR/file
    hs --json objective delete do-not-move -e true $TDIR/file
    hs --json objective delete --force do-not-move -e true $TDIR/file
    # This next line is expected to fail
#    hs --json objective delete do-not-move $TDIR/file
    hs --json objective add "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/file
    hs --json objective has "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/file
    hs --json objective add "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs --json objective has "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs --json objective add "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/file
    hs --json objective delete "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs --json objective delete --force "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/file
    hs --json objective has "Place-on-Node11.rw.net"  $TDIR/file
    hs --json objective has do-not-move $TDIR/file
    # RECURSIVE OBJECTIVE RELATED
    hs --json objective add --recursive "do-not-move" -e true $TDIR/
    hs --json objective has --recursive "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --raw "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --compact "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --local "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --local --raw "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --local --compact "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --inherited "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --inherited --raw "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --inherited --compact "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --effective "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --effective --raw "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --effective --compact "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --active "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --active --raw "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --active --compact "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --share "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --share --raw "do-not-move" -e true $TDIR/
    hs --json objective has --recursive --share --compact "do-not-move" -e true $TDIR/
    hs --json objective delete --recursive "do-not-move" -e true $TDIR/
    hs --json objective delete --recursive --force "do-not-move" -e true $TDIR/
    hs --json objective add --recursive "do-not-move" $TDIR/ # implied -e true
    hs --json objective delete --recursive "do-not-move" $TDIR/
    hs --json objective add --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/
    hs --json objective add --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/
    hs --json objective delete --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(IS_LIVE)" $TDIR/
    hs --json objective delete --recursive "Place-on-Node11.rw.net" -e "EXPRESSION(SPACE_USED>10KBYTES)" $TDIR/
}

function test_collections {
    # COLLECTION RELATED
    hs eval -e "is_in(COLLECTION('open'))" $TDIR/file
    hs attribute set selected -e true $TDIR/dir1/dir2/file $TDIR/dir1/dir2/dir3/dir4/file $TDIR/dir1/dir2/dir3/dir4/dir5
    hs eval --recursive -e "IF size<1byte THEN PATH" $TDIR
    hs eval --recursive -e "IF attributes.selected THEN PATH" $TDIR
    hs eval --symlink $TDIR/selectedfiles --recursive -e "IF attributes.selected THEN PATH" $TDIR
    cat $TDIR/selectedfiles
    rm $TDIR/selectedfiles

    # 3 ways to "search" for files
    ls $TDIR/.collections/open
    hs eval --recursive -e "IF SIZE>5BYTES THEN PATH" $TDIR
    hs attribute set selected -e "EXPRESSION(SIZE>5BYTES)" $TDIR
    ls $TDIR/.collections/selected
    hs attribute set selected -e "EXPRESSION(SIZE>5BYTES AND FNMATCH('*il*',name))" $TDIR
    ls $TDIR/.collections/selected

    hs eval -e "collection_sums('all')" $TDIR
    hs eval -e "collection_sums('open')" $TDIR
}

function test_collections_json {
    # COLLECTION RELATED
    hs --json eval -e "is_in(COLLECTION('open'))" $TDIR/file
    hs --json attribute set selected -e true $TDIR/dir1/dir2/file $TDIR/dir1/dir2/dir3/dir4/file $TDIR/dir1/dir2/dir3/dir4/dir5
    hs --json eval --recursive -e "IF size<1byte THEN PATH" $TDIR
    hs --json eval --recursive -e "IF attributes.selected THEN PATH" $TDIR
    hs --json eval --symlink $TDIR/selectedfiles --recursive -e "IF attributes.selected THEN PATH" $TDIR
    cat $TDIR/selectedfiles
    rm $TDIR/selectedfiles

    # 3 ways to "search" for files
    ls $TDIR/.collections/open
    hs --json eval --recursive -e "IF SIZE>5BYTES THEN PATH" $TDIR
    hs --json attribute set selected -e "EXPRESSION(SIZE>5BYTES)" $TDIR
    ls $TDIR/.collections/selected
    hs --json attribute set selected -e "EXPRESSION(SIZE>5BYTES AND FNMATCH('*il*',name))" $TDIR
    ls $TDIR/.collections/selected

    hs --json eval -e "collection_sums('all')" $TDIR
    hs --json eval -e "collection_sums('open')" $TDIR
}

function test_sums {
    # SUMS RELATED
    # Total number of INODES of each type
    hs sum -e "SUMS_TABLE{TYPE,{1FILE,space_used,size}}" $TDIR
    hs sum --raw -e "SUMS_TABLE{TYPE,{1FILE,space_used,size}}" $TDIR
    hs sum --compact -e "SUMS_TABLE{TYPE,{1FILE,space_used,size}}" $TDIR
    # How many files, how much space and the top 10 largest files on each volume
    hs sum -e "SUMS_TABLE{|::NAME=INSTANCES[ROW].VOLUME,|::VALUE={1,INSTANCES[ROW].SPACE_USED}}[ROWS(INSTANCES)]" $TDIR

    # How many files, how much space and the top 10 largest files at each level of alignment
    hs sum -e "IS_FILE?SUMS_TABLE{IFERROR(OVERALL_ALIGNMENT,#EMPTY),{1FILE,SPACE_USED,TOP10_TABLE{{SPACE_USED,PATH}}}}" $TDIR
    # How many files, how much space and the top 10 largest files on each owner
    hs sum -e "IS_FILE?SUMS_TABLE{IFERROR(OWNER,#EMPTY),{1FILE,SPACE_USED,TOP10_TABLE{{space_used,path}}}}" $TDIR

    # TOP AND BOTTOM 10,100, and 1000
    hs sum -e "TOP10_TABLE{{space_used,path}}" $TDIR
    hs sum -e "TOP100_TABLE{{space_used,path}}" $TDIR
    hs sum -e "TOP1000_TABLE{{space_used,path}}" $TDIR
    hs sum -e "BOTTOM10_TABLE{{space_used,path}}" $TDIR
    hs sum -e "BOTTOM100_TABLE{{space_used,path}}" $TDIR
    hs sum -e "BOTTOM1000_TABLE{{space_used,path}}" $TDIR

    hs sum --symlink $TDIR/volume_sums -e "SUMS_TABLE{|::NAME=INSTANCES[ROW].VOLUME,|::VALUE={1,INSTANCES[ROW].SPACE_USED,TOP10_TABLE{{space_used,path}}}}[ROWS(INSTANCES)]" $TDIR
    cat $TDIR/volume_sums
    rm $TDIR/volume_sums
}

function test_sums_json {
    # SUMS RELATED
    # Total number of INODES of each type
    hs --json sum -e "SUMS_TABLE{TYPE,{1FILE,space_used,size}}" $TDIR
    hs --json sum --raw -e "SUMS_TABLE{TYPE,{1FILE,space_used,size}}" $TDIR
    hs --json sum --compact -e "SUMS_TABLE{TYPE,{1FILE,space_used,size}}" $TDIR
    # How many files, how much space and the top 10 largest files on each volume
    hs --json sum -e "SUMS_TABLE{|::NAME=INSTANCES[ROW].VOLUME,|::VALUE={1,INSTANCES[ROW].SPACE_USED}}[ROWS(INSTANCES)]" $TDIR

    # How many files, how much space and the top 10 largest files at each level of alignment
    hs --json sum -e "IS_FILE?SUMS_TABLE{IFERROR(OVERALL_ALIGNMENT,#EMPTY),{1FILE,SPACE_USED,TOP10_TABLE{{SPACE_USED,PATH}}}}" $TDIR
    # How many files, how much space and the top 10 largest files on each owner
    hs --json sum -e "IS_FILE?SUMS_TABLE{IFERROR(OWNER,#EMPTY),{1FILE,SPACE_USED,TOP10_TABLE{{space_used,path}}}}" $TDIR

    # TOP AND BOTTOM 10,100, and 1000
    hs --json sum -e "TOP10_TABLE{{space_used,path}}" $TDIR
    hs --json sum -e "TOP100_TABLE{{space_used,path}}" $TDIR
    hs --json sum -e "TOP1000_TABLE{{space_used,path}}" $TDIR
    hs --json sum -e "BOTTOM10_TABLE{{space_used,path}}" $TDIR
    hs --json sum -e "BOTTOM100_TABLE{{space_used,path}}" $TDIR
    hs --json sum -e "BOTTOM1000_TABLE{{space_used,path}}" $TDIR

    hs --json sum --symlink $TDIR/volume_sums -e "SUMS_TABLE{|::NAME=INSTANCES[ROW].VOLUME,|::VALUE={1,INSTANCES[ROW].SPACE_USED,TOP10_TABLE{{space_used,path}}}}[ROWS(INSTANCES)]" $TDIR
    cat $TDIR/volume_sums
    rm $TDIR/volume_sums
}

test_attributes_json
test_tags_json
test_rekognition_tags_json
test_keywords_json
test_labels_json
test_objectives_json
test_collections_json
test_sums_json


test_attributes
test_tags
test_rekognition_tags
test_keywords
test_labels
test_objectives
test_collections
test_sums




