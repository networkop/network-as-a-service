#!/bin/bash

ROOT=$(cd $(dirname $0); pwd)
CA_CRT="${ROOT}/certs/ca.crt"
CA_KEY="${ROOT}/certs/ca.key"

set -o errexit
set -o nounset
set -o pipefail

if [ ! -x "$(command -v openssl)" ]; then
    echo "openssl not found"
    exit 1
fi

# Cleanup any existing CAs
if [ -f ${CA_CRT} ]; then
    rm -f ${CA_CRT}
fi

if [ -f ${CA_KEY} ]; then
    rm -f ${CA_KEY}
fi

# Generate CA cert
openssl genrsa -out ${CA_KEY} 2048
openssl req -x509 -new -nodes -key ${CA_KEY} -days 100000 \
        -out ${CA_CRT} -subj "/CN=admission_ca"



export CA_BUNDLE=$(cat ${CA_CRT} | base64 | tr -d '\n')

if command -v envsubst >/dev/null 2>&1; then
    envsubst
else
    sed -e "s|\${CA_BUNDLE}|${CA_BUNDLE}|g"
fi