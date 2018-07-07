#!/bin/bash

PYTHON_EXECUTABLE_PATH=$1
MAKERUN="${PYTHON_EXECUTABLE_PATH} ~/src/cloudhome/cloudhome/cloudhome.py"
PROCESS="cloudhome.py"

if ps ax | grep -v grep | grep "$PROCESS" > /dev/null
then
    exit
else
    eval "${MAKERUN} &"
fi

exit
