#!/bin/sh
# Local teaching TLS materials. NEVER trust/deploy these outside this lab.
# Usage: sh generate-fixtures.sh /absolute/path/to/NEW-directory
set -eu
umask 077
OPENSSL=${OPENSSL:-/usr/bin/openssl}
if [ "$#" -ne 1 ]; then
  echo "usage: generate-fixtures.sh /absolute/path/to/NEW-directory" >&2; exit 2
fi
case "$1" in /*) ;; *) echo "output must be absolute" >&2; exit 2 ;; esac
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# mkdir refuses existing files, directories and symlinks; no old output is replaced.
mkdir -m 700 "$1"
cd -- "$1"
cp "$SCRIPT_DIR/ca.cnf" ca.cnf
cp "$SCRIPT_DIR/server.cnf" server.cnf
"$OPENSSL" version > openssl-version.txt
"$OPENSSL" req -new -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 -config ca.cnf -keyout ca-public-fixture.key -out ca.pem
"$OPENSSL" req -new -newkey rsa:2048 -nodes -sha256 -config server.cnf -keyout server-public-fixture.key -out server.csr
"$OPENSSL" x509 -req -in server.csr -CA ca.pem -CAkey ca-public-fixture.key -set_serial 17502 -days 3650 -sha256 -extfile server.cnf -extensions server -out server.pem
"$OPENSSL" verify -CAfile ca.pem server.pem
"$OPENSSL" x509 -in server.pem -noout -text > server-certificate.txt
mkdir -p android-res/raw
cp ca.pem android-res/raw/wwl_public_ca.pem
