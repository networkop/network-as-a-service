#!/bin/sh

GIT_DIR="code"
GIT_COMMIT_MSG="NaaS run $(eval date)"

case $1 in 
git-clone)
  command="git clone --depth 1 ${2} ${GIT_DIR}; cd ${GIT_DIR}"
  ;;
git-push)
  command="git add -A config/; git commit -m \"${GIT_COMMIT_MSG}\"; git push ${2}"
  ;;
sleep)
  command="tail -f /dev/null"
  ;;
*)
  echo "Unrecognised input. Arguments passed: $@"
esac

if [ ! -z ${command+x} ]; then
  echo "Executing command ${command}"
  eval $command
else
  echo "Nothing to execute. Exiting."
  exit 1
fi
