#!/bin/bash

function scriptDone {
    echo "---> DONE"
    exit 0
}

function printLine {
    echo "------------------------------------------------------------------------------"
}

NAME=imapmanager

# The option "--no-cache" is used to rebuild the image if the python source code has changed

echo "---> Do you want to build the latest image of ${NAME}? [y/n]"
read -r answer
if [[ "${answer}" == "y" ]]; then
    docker build -t registry.pofilo.fr/"${NAME}":latest . --no-cache --progress=plain
    scriptDone
fi

# Get most recent tag
VERSION=$(git describe --tags "$(git rev-list --tags --max-count=1)")

printLine
echo "---> Do you want to build the ${VERSION} image of ${NAME}? [y/n]"
read -r answer
if [[ "${answer}" == "y" ]]; then
    docker build -t registry.pofilo.fr/"${NAME}":"${VERSION}" . --no-cache
    ret=$?
    if [ "${ret}" -ne 0 ]; then
        echo "Something went wrong .."
        exit 1
    fi
else
    scriptDone
fi

printLine
echo "---> Do you want to push the ${VERSION} image of ${NAME}? [y/n]"
read -r answer
if [[ "${answer}" == "y" ]]; then
    docker push registry.pofilo.fr/"${NAME}":"${VERSION}"
fi

scriptDone


