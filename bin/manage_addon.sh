#!/bin/bash
# Copyright 2015 Solinea, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

export DJANGO_SETTINGS_MODULE=goldstone.settings.docker_dev
DOCKER_VM="default"
APP_CONTAINER=goldstoneserver_gsappdev_1
VERBOSE=false
ADDON_NAME=""
ADDON_FILE=""
MODULE_NAME=""
OPERATION="install"

TOP_DIR=${GS_PROJ_TOP_DIR:-~/devel/goldstone-server}

function usage() {
    echo "Usage: $0 [--install] [--verbose] --addon-name=name --addon-file=filename [--docker-vm=name] [--app-container=name] |"
    echo "          --uninstall --addon-name=name --package-name=py-package [--docker-vm=name] [--app-container=name]"
}


for arg in "$@" ; do
    case $arg in
        --install)
            OPERATION=install
        ;;
        --uninstall)
            OPERATION=uninstall
        ;;
        --verbose)
            VERBOSE=true
        ;;
        --docker-vm=*)
            DOCKER_VM="${arg#*=}"
            shift
        ;;
        --app-container=*)
            APP_CONTAINER="${arg#*=}"
            shift
        ;;
        --addon-name=*)
            ADDON_NAME="${arg#*=}"
            shift
        ;;
        --package-name=*)
            MODULE_NAME="${arg#*=}"
            shift
        ;;
        --addon-file=*)
            ADDON_FILE="${arg#*=}"
            shift
        ;;
        --help)
            usage
            exit 0
        ;;
        *)
            # unknown option
            usage
            exit 1
        ;;
    esac
done

cd $TOP_DIR || exit 1

if [[ ${ADDON_NAME} == "" ]] ; then
    usage
    exit 1
fi

  
docker-machine start ${DOCKER_VM}
eval "$(docker-machine env ${DOCKER_VM})"

if [[ $(docker ps -f name=goldstoneserver_gsappdev_1 --format "{{.ID}}" | sed -n '$=') != "1" ]] ; then
    echo "Container ${APP_CONTAINER} must be running.  Did you run start_dev_env.sh first?"
    exit 1
fi

if [[ ${OPERATION} == "install" ]] ; then
    if [ ! -f "addons/${ADDON_FILE}" ] ; then
        echo "Addon file not found.  It must be in ${TOP_DIR}/addons during installation, but can be removed afterwards."
        exit 1
    fi
    PIP_CMD="pip install --upgrade addons/${ADDON_FILE}"
    FAB_CMD="fab -f addon_fabfile.py install_addon:name=${ADDON_NAME},install_dir=.,settings=${DJANGO_SETTINGS_MODULE},verbose=${VERBOSE}"
    docker exec -t ${APP_CONTAINER} bash -i -c "$PIP_CMD" || { echo "Failed to install pip module"; exit 1; }
    docker exec -i -t ${APP_CONTAINER} bash -i -c "$FAB_CMD" || { echo "Failed to install addon"; exit 1; }
    grep ${ADDON_FILE} addon-requirements.txt || echo "addons/${ADDON_FILE}  # addon=${ADDON_NAME}" >> addon-requirements.txt
else
    if [[ ${MODULE_NAME} == "" ]] ; then
        usage
        exit 1
    fi
    FAB_CMD="fab -f addon_fabfile.py remove_addon:name=${ADDON_NAME},install_dir=.,settings=${DJANGO_SETTINGS_MODULE}"
    PIP_CMD="yes | pip uninstall ${MODULE_NAME}"
    docker exec -i -t ${APP_CONTAINER} bash -i -c "$FAB_CMD" || { echo "Failed to remove addon"; exit 1; }
    docker exec -i -t ${APP_CONTAINER} bash -i -c "$PIP_CMD" || { echo "Failed to remove pip module. Continuing."; }
    sed -i '' "/addon=${ADDON_NAME}/d" addon-requirements.txt
fi

docker commit ${APP_CONTAINER}

echo ""
echo "Restart the dev environment to complete the addon change process."
echo ""

