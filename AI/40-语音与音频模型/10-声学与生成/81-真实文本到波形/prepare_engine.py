#!/usr/bin/env python3
"""Prepare pinned local eSpeak dependency, no global installation. Preparation, not training.
Requires C/C++ compiler, cmake, curl, ar. 4 build jobs, runtime wrapper needs NumPy.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

SOURCES=[('espeak-src','https://api.github.com/repos/espeak-ng/espeak-ng/tarball/1.52.0','2b56ec2b03a19e63ea5ead7f605a1d6adac33c19859c23a6da7b0c618fb7dddf'),
         ('sonic','https://api.github.com/repos/waywardgeek/sonic/tarball/fbf75c3d6d846bad3bb3d456cbc5d07d9fd8c104','6e60badda11fc663a771281cd731a8cc51cb8c24ab0fbc5c810aced0d2cd43ce')]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
    work=a.work.resolve()
    if work.exists() and any(work.iterdir()):raise ValueError('use a new empty work directory; existing preparation remains intact')
    work.mkdir(parents=True,exist_ok=True)
    for name,url,digest in SOURCES:
        archive=work/(name+'.tar.gz');subprocess.run(['curl','-L','--fail','--silent','--show-error',url,'-o',str(archive)],check=True)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=digest:raise ValueError('archive identity changed: '+name)
        dest=work/name;dest.mkdir();subprocess.run(['tar','-xzf',str(archive),'--strip-components=1','-C',str(dest)],check=True)
    sonic=work/'sonic';src=work/'espeak-src';build=work/'espeak-out';install=work/'espeak-install'
    subprocess.run(['cc','-O2','-fPIC','-c',str(sonic/'sonic.c'),'-o',str(sonic/'sonic.o')],check=True)
    subprocess.run(['ar','rcs',str(sonic/'libsonic.a'),str(sonic/'sonic.o')],check=True)
    subprocess.run(['cmake','-S',str(src),'-B',str(build),'-DSONIC_LIB='+str(sonic/'libsonic.a'),'-DSONIC_INC='+str(sonic),
        '-DUSE_LIBPCAUDIO=OFF','-DUSE_ASYNC=OFF','-DUSE_MBROLA=OFF','-DUSE_SPEECHPLAYER=OFF','-DBUILD_SHARED_LIBS=ON',
        '-DCMAKE_INSTALL_PREFIX='+str(install),'-DCMAKE_BUILD_TYPE=Release'],check=True)
    def compile_install():
        subprocess.run(['cmake','--build',str(build),'--parallel','4'],check=True)
        subprocess.run(['cmake','--install',str(build)],check=True)
    compile_install()
    here=Path(__file__).resolve().parent
    def worker(dest):
        dest.mkdir();subprocess.run([sys.executable,'-B',str(here/'tts_lab.py'),'--worker','--engine',str(install),'--output',str(dest),
            '--case','proof','--text','I paid twelve dollars and fifty cents on April third.'],check=True)
    before=work/'unmodified-proof';worker(before)
    subprocess.run([sys.executable,'-B',str(here/'instrument_wavegen.py'),str(src)],check=True);compile_install()
    after=work/'instrumented-proof';worker(after)
    if (before/'proof.wav').read_bytes()!=(after/'proof.wav').read_bytes():raise ValueError('observational insertion changed fixed-probe PCM')
    print('Pinned engine ready; observational-insertion fixed-probe PCM identical:',hashlib.sha256((after/'proof.wav').read_bytes()).hexdigest())
    print('Use --engine',install)

if __name__=='__main__':main()
