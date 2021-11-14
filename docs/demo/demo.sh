#!/bin/bash

########################
# include the magic
########################
. demo-magic.sh

# hide the evidence
clear

# Put your stuff here
PROMPT_TIMEOUT=1

pei "# Let's perform the one-time setup of filetailor."
wait
pei "filetailor init"
wait
#pei "y"
#wait
pei "filetailor init"
wait
#pei "y"
#wait
#pei "y"
#wait
#pei "y"
#wait
pei "# Setup is complete. Let's create a file and back it up."
wait
pei "echo foo > file.txt"
wait
pei "filetailor add file.txt"
wait
#pei "y"
#wait
pei "filetailor backup file.txt"
wait
#pei "y"
#wait
pei "# The file is backed up. Now let's restore the file."
wait
pei "filetailor restore file.txt"
wait
pei "# The file did not change, so a restore was not necessary. Let's change the file and try restore again."
wait
pei "echo bar > file.txt"
wait
pei "filetailor restore"
#wait
#pei "y"
