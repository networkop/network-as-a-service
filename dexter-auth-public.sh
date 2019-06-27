#!/bin/bash
echo 'Launching interactive authentication'
dexter auth -i \
       uuid.apps.googleusercontent.com \
       -s my.oauth.secret \
       -k /home/user/.kube/kind-config-naas

echo 'Settings context for the new user'
kubectl config set-context mk \
        --cluster=naas \
        --user=my.gmail.user.account@gmail.com \
        --namespace=tenant-a