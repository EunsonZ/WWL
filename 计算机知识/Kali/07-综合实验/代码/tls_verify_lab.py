#!/usr/bin/env python3
"""Offline OpenSSL certificate verification laboratory (tls-v3.1).

Generates ephemeral EC test keys only inside a private temporary directory. No
listener, TLS handshake, network lookup, installation, or system trust-store change.
Prints commands/results but never key bytes; removes temporary files on exit (not a
secure-erasure promise). Requires an existing OpenSSL 3.x CLI; stdlib Python >=3.10.
Do not copy the short-lived test CA policy into a production PKI.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def _epoch(text: str) -> int:
    """Parse the fixed English GMT date output emitted with LC_ALL=C."""
    date = text.strip().split('=', 1)[1].split()
    if len(date) != 5 or date[-1] != 'GMT':
        raise ValueError('unexpected certificate date format')
    month = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(date[0])+1
    hour, minute, second = map(int, date[2].split(':'))
    return int(datetime(int(date[3]), month, int(date[1]), hour, minute, second,
                        tzinfo=timezone.utc).timestamp())


def assess_verification(returncode: int, stdout: str, stderr: str,
                        expected_accept: bool, expected_error_code: int | None = None) -> dict:
    """Bounded OpenSSL 3.x CLI oracle; unsupported diagnostics must not pass silently.

    LC_ALL=C is imposed by the caller. This parses only documented verification
    diagnostics observed by this exercise, not arbitrary OpenSSL command errors.
    """
    errors = [int(x) for x in re.findall(r'^error (\d+) at \d+ depth lookup:', stderr, re.M)]
    accepted = returncode == 0 and not errors and stdout.rstrip().endswith(': OK')
    if expected_accept:
        passed = accepted and expected_error_code is None
    else:
        passed = (returncode == 2 and expected_error_code is not None
                  and set(errors) == {expected_error_code}
                  and 'verification failed' in stderr)
    return {'expected_accept': expected_accept, 'observed_accept': accepted,
            'expected_error_code': expected_error_code, 'observed_error_codes': errors,
            'passed': passed}


def run() -> dict:
    executable = shutil.which('openssl')
    if executable is None:
        raise RuntimeError('OpenSSL is missing; no TLS verification tests ran')
    version = subprocess.run([executable, 'version'], capture_output=True, text=True,
                             timeout=10, check=True).stdout.strip()
    if not version.startswith('OpenSSL 3.'):
        raise RuntimeError('this exercise targets OpenSSL 3.x, not an unverified CLI dialect')
    setup = []
    with tempfile.TemporaryDirectory(prefix='kali-tls-offline-') as folder:
        root = Path(folder)
        root.chmod(0o700)
        conf = root/'openssl.cnf'
        conf.write_text('openssl_conf = openssl_init\n[openssl_init]\n[req]\ndistinguished_name = dn\n[dn]\n')
        env = os.environ.copy()
        env.update({'LC_ALL':'C', 'OPENSSL_CONF':str(conf)})
        env.pop('OPENSSL_MODULES', None)
        def command(args: list[str], *, required: bool=True, record: bool=True) -> dict:
            proc = subprocess.run([executable, *args], cwd=root, env=env,
                                  capture_output=True, text=True, timeout=15)
            result = {'command':['openssl', *args], 'returncode':proc.returncode,
                      'stdout':proc.stdout.replace(str(root),'<temporary>'),
                      'stderr':proc.stderr.replace(str(root),'<temporary>')}
            if record: setup.append(result)
            if required and proc.returncode:
                raise RuntimeError('OpenSSL setup failed: '+json.dumps(result))
            return result
        key_args = ['-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-noenc']
        def self_signed(name: str) -> None:
            command(['req','-x509',*key_args,'-days','3','-subj','/CN='+name,
                     '-keyout',name+'.key','-out',name+'.pem',
                     '-addext','basicConstraints=critical,CA:TRUE,pathlen:1',
                     '-addext','keyUsage=critical,keyCertSign,cRLSign',
                     '-addext','subjectKeyIdentifier=hash'])
            (root/(name+'.key')).chmod(0o600)
        self_signed('lab-root');self_signed('unrelated-root')
        command(['req','-new',*key_args,'-subj','/CN=lab-intermediate',
                 '-keyout','intermediate.key','-out','intermediate.csr'])
        (root/'intermediate.key').chmod(0o600)
        (root/'intermediate.ext').write_text(
            'basicConstraints=critical,CA:TRUE,pathlen:0\n'
            'keyUsage=critical,keyCertSign,cRLSign\n'
            'subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n')
        command(['x509','-req','-in','intermediate.csr','-CA','lab-root.pem',
                 '-CAkey','lab-root.key','-set_serial','2','-days','2',
                 '-extfile','intermediate.ext','-out','intermediate.pem'])
        command(['req','-new',*key_args,'-subj','/CN=synthetic-leaf',
                 '-keyout','leaf.key','-out','leaf.csr'])
        (root/'leaf.key').chmod(0o600)
        (root/'leaf.ext').write_text(
            'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\n'
            'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:web.lab.test,IP:127.0.0.1\n'
            'subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n')
        command(['x509','-req','-in','leaf.csr','-CA','intermediate.pem',
                 '-CAkey','intermediate.key','-set_serial','3','-days','1',
                 '-extfile','leaf.ext','-out','leaf.pem'])
        dates = command(['x509','-in','leaf.pem','-noout','-dates'])['stdout'].splitlines()
        start, end = _epoch(dates[0]), _epoch(dates[1])
        command(['x509','-in','leaf.pem','-outform','DER','-out','leaf.der'])
        corrupted = bytearray((root/'leaf.der').read_bytes())
        corrupted[-1] ^= 1  # Alter the final signature byte, not the public names or ASN.1 layout.
        (root/'tampered.der').write_bytes(corrupted)
        command(['x509','-inform','DER','-in','tampered.der','-out','tampered.pem'])
        common = ['verify','-no-CAfile','-no-CApath','-no-CAstore']
        def verification(ca='lab-root.pem', intermediate=True, purpose='sslserver',
                         identity=None, attime=None, leaf='leaf.pem'):
            args = [*common,'-CAfile',ca]
            if intermediate: args += ['-untrusted','intermediate.pem']
            if purpose is not None: args += ['-purpose',purpose]
            if identity is not None: args += list(identity)
            if attime is not None: args += ['-attime',str(attime)]
            return [*args,leaf]
        host = ('-verify_hostname','web.lab.test')
        cases = [
            ('valid_dns_identity',True,verification(identity=host)),
            ('valid_ip_identity',True,verification(identity=('-verify_ip','127.0.0.1'))),
            ('wrong_dns_identity',False,verification(identity=('-verify_hostname','other.lab.test'))),
            ('wrong_ip_identity',False,verification(identity=('-verify_ip','127.0.0.2'))),
            ('missing_intermediate',False,verification(intermediate=False,identity=host)),
            ('unrelated_trust_anchor',False,verification(ca='unrelated-root.pem',identity=host)),
            ('wrong_extended_key_usage',False,verification(purpose='sslclient',identity=host)),
            ('before_validity',False,verification(identity=host,attime=start-1)),
            ('after_validity',False,verification(identity=host,attime=end+1)),
            ('chain_without_identity_check',True,verification(identity=None)),
            ('changed_signature_byte',False,verification(identity=host,leaf='tampered.pem')),
        ]
        expected_errors = {'wrong_dns_identity':62, 'wrong_ip_identity':64,
            'missing_intermediate':20, 'unrelated_trust_anchor':20,
            'wrong_extended_key_usage':26, 'before_validity':9,
            'after_validity':10, 'changed_signature_byte':7}
        results=[]
        for label,expected,args in cases:
            result=command(args,required=False,record=False)
            result['id'] = label
            result.update(assess_verification(result['returncode'], result['stdout'],
                          result['stderr'], expected, expected_errors.get(label)))
            results.append(result)
        private_modes={p.name:oct(p.stat().st_mode & 0o777) for p in root.glob('*.key')}
        report={'model':'tls-v3.1','openssl_version':version,'synthetic':True,
                'network_io':False,'system_trust_modified':False,'setup_commands':setup,
                'key_permissions':private_modes,'cases':results,
                'case_count':len(results),'passed_count':sum(x['passed'] for x in results),
                'not_tested':['TLS handshake','revocation/OCSP/CRL','browser behavior',
                              'live server possession of private key','all OpenSSL versions']}
    report['temporary_files_removed']=not root.exists()
    report['status']='passed' if all(x['passed'] for x in results) and not root.exists() else 'failed'
    return report

if __name__=='__main__':
    try:
        result=run()
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        print(json.dumps({'status':'failed_or_not_run','error':str(exc)},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['status']=='passed' else 1)
