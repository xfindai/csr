# !/bin/bash
SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_PATH
git pull
. venv/bin/activate
#echo "done $(date)"> test.log
python run.py config.yaml