# !/bin/bash
SCRIPT_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_PATH
git pull
. venv/bin/activate

echo "Starting Scheduled pull task at $(date)" > scheduled_tasks.log

python run.py config.yaml

echo "Completed Scheduled pull task at $(date)" > scheduled_tasks.log