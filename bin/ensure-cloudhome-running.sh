#!/bin/bash

PYTHON_EXECUTABLE_PATH=$1
PROCESS="${PYTHON_EXECUTABLE_PATH} ~/src/cloudhome/cloudhome/cloudhome.py"

if ps ax | grep -v grep | grep "$PROCESS" > /dev/null
then
    exit
else
    eval "${PROCESS} &"
fi

exit
