#!/bin/bash
#set -x
export img=IMAGE
export CONTAINERENV_FI_PROVIDER=tcp
export CONTAINERENV_FI_PROVIDER_PATH=FI_PATH
export SINGULARITY_SHELL=/bin/bash
cmd=BASEFILE
arg="$@"
singularity exec -e BINDDIRS "${img}" $cmd $arg

