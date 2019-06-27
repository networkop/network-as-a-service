#!/bin/bash

ROOT=$(cd $(dirname $0); pwd)
CA_CRT="${ROOT}/certs/ca.crt"
CA_KEY="${ROOT}/certs/ca.key"

set -x

usage() {
    cat <<EOF
Generate certificate suitable for use with an sidecar-injector webhook service.

This script uses k8s' CertificateSigningRequest API to a generate a
certificate signed by k8s CA suitable for use with sidecar-injector webhook
services. This requires permissions to create and approve CSR. See
https://kubernetes.io/docs/tasks/tls/managing-tls-in-a-cluster for
detailed explantion and additional instructions.

The server key/cert k8s CA cert are stored in a k8s secret.

usage: ${0} [OPTIONS]

The following flags are required.

       --service          Service name of webhook.
       --namespace        Namespace where webhook service and secret reside.
       --secret           Secret name for CA certificate and server certificate/key pair.
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case ${1} in
        --service)
            service="$2"
            shift
            ;;
        --secret)
            secret="$2"
            shift
            ;;
        --namespace)
            namespace="$2"
            shift
            ;;
        *)
            usage
            ;;
    esac
    shift
done

[ -z ${service} ] && service=opa
[ -z ${secret} ] && secret=opa-server
[ -z ${namespace} ] && namespace=opa

if [ ! -x "$(command -v openssl)" ]; then
    echo "openssl not found"
    exit 1
fi

if [[ ! -f ${CA_KEY} || ! -f ${CA_CRT} ]]; then
    echo "CA key/certificate not found"
    exit 1
fi

# clean-up any previously created secrets
kubectl delete secret tls ${secret} -n ${namespace} 2>/dev/null || true

csrName=${service}.${namespace}
tmpdir=$(mktemp -d)
echo "creating certs in tmpdir ${tmpdir} "

cat <<EOF >> ${tmpdir}/csr.conf
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${service}
DNS.2 = ${service}.${namespace}
DNS.3 = ${service}.${namespace}.svc
EOF

openssl genrsa -out ${tmpdir}/server-key.pem 2048
openssl req -new -key ${tmpdir}/server-key.pem \
        -subj "/CN=${service}.${namespace}.svc" \
        -out ${tmpdir}/server.csr \
        -config ${tmpdir}/csr.conf


openssl x509 -req -in ${tmpdir}/server.csr \
        -CA ${CA_CRT} -CAkey ${CA_KEY} -CAcreateserial \
        -out ${tmpdir}/server-cert.pem -days 100000 \
        -extensions v3_req \
        -extfile ${tmpdir}/csr.conf

# create the TLS secret with CA cert and server cert/key
kubectl create secret tls ${secret} \
        --key=${tmpdir}/server-key.pem \
        --cert=${tmpdir}/server-cert.pem \
        --dry-run -o yaml |
    kubectl -n ${namespace} apply -f -
