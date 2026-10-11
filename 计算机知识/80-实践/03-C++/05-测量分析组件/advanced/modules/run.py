#!/usr/bin/env python3
"""Clang named-module experiment: full rebuild, P1689 graph, runtime/negative checks.
Only the explicitly supplied build directory is written. No installation/download.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', required=True, type=Path)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--cxx', default='clang++')
    parser.add_argument('--config', choices=['Debug', 'Release'], default='Debug')
    args = parser.parse_args()
    vault, build = args.vault.resolve(), args.build.resolve()
    here = Path(__file__).resolve().parent
    if build.exists():
        raise SystemExit('Use a new build directory; existing evidence is never overwritten.')
    if build == vault or vault in build.parents or build == here or here in build.parents:
        raise SystemExit('Build directory must be outside the source vault and module source.')
    cxx = shutil.which(args.cxx)
    if not cxx:
        raise SystemExit('C++ compiler not found: ' + args.cxx)
    # Keep the clang++ driver name: resolving its symlink to clang changes
    # default C++ runtime linkage. Resolve only the containing directory.
    cxx = str(Path(cxx).absolute())
    scanner = str(Path(cxx).parent.resolve()/'clang-scan-deps')
    if not Path(scanner).is_file():
        raise SystemExit('Matching clang-scan-deps is required beside the selected compiler.')
    build.mkdir(parents=True)
    log = (build/'commands.log').open('w')

    def run(command, expected=0, pattern=None):
        log.write('$ ' + shlex.join(map(str, command)) + '\n')
        log.flush()
        result = subprocess.run(list(map(str, command)), text=True, capture_output=True, cwd=build)
        output = result.stdout + result.stderr
        log.write(output + f'\nexit={result.returncode}\n')
        log.flush()
        if (expected == 0 and result.returncode != 0) or (expected != 0 and result.returncode == 0):
            raise RuntimeError('Unexpected exit; see commands.log: ' + shlex.join(map(str, command)))
        if pattern and pattern not in output:
            raise RuntimeError('Required diagnostic absent: ' + pattern)
        return result

    for command in [[cxx, '--version'], [scanner, '--version'], ['cmake', '--version'], ['uname', '-srm']]:
        run(command)
    component = vault/'计算机知识/80-实践/03-C++/05-测量分析组件'
    originals = list((component/'include/wwl').glob('*.hpp')) + list((component/'src').glob('*.cpp'))
    originals += [component/'CMakeLists.txt', component/'data/report-reference.txt',
                  component/'../02-RAII与张量缓冲区/tensor_buffer.hpp',
                  component/'../04-布局缓存与并行归约/layout_math.hpp']
    identities = {str(p.relative_to(vault)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in originals if p.is_file()}
    (build/'original-source-sha256.json').write_text(json.dumps(identities, indent=2, ensure_ascii=False)+'\n')
    prefix = build/'prefix'
    run(['cmake', '-S', component, '-B', build/'legacy', '-G', 'Unix Makefiles',
         '-DCMAKE_CXX_COMPILER='+cxx, '-DCMAKE_BUILD_TYPE='+args.config,
         '-DBUILD_TESTING=OFF', '-DCMAKE_INSTALL_PREFIX='+str(prefix)])
    run(['cmake', '--build', build/'legacy', '--target', 'measurement', '--parallel', '2'])
    run(['cmake', '--install', build/'legacy'])
    library = prefix/'lib/libmeasurement.a'
    if not library.is_file():
        raise RuntimeError('Expected static install path missing: ' + str(library))
    flags = ['-std=c++20', '-Wall', '-Wextra', '-Wpedantic', '-fno-fast-math',
             '-ffp-contract=off', '-I'+str(prefix/'include'), '-I'+str(here), '-pthread']
    flags += ['-O0', '-g'] if args.config == 'Debug' else ['-O3', '-DNDEBUG']
    run([cxx, *flags, '-dM', '-E', '-x', 'c++', '-include', 'version', '/dev/null'])
    units = ['wwl.measurement.cppm', 'wwl.measurement.cpp', 'importer.cpp']
    commands = []
    for unit in units:
        source, obj = here/unit, build/(unit+'.o')
        commands.append({'directory': str(build), 'file': str(source), 'output': str(obj),
                         'arguments': [cxx, *flags, '-c', str(source), '-o', str(obj)]})
    (build/'compile_commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    run([scanner, '-format=p1689', '-compilation-database='+str(build/'compile_commands.json'),
         '-j', '1', '-o', build/'dependencies.json'])
    rules = json.loads((build/'dependencies.json').read_text())['rules']
    by_output = {item['output']: item for item in commands}
    providers = {}
    for rule in rules:
        for provision in rule.get('provides', []):
            name = provision['logical-name']
            if name in providers:
                raise RuntimeError('Duplicate module provider: ' + name)
            if not provision.get('is-interface'):
                raise RuntimeError('This example requires interface providers only.')
            providers[name] = rule['primary-output']
    if set(providers) != {'wwl.measurement'} or len(rules) != len(commands):
        raise RuntimeError('Unexpected scanned graph.')
    pending, done, pcm_by_name = list(rules), set(), {}
    order = []
    while pending:
        progress = False
        for rule in pending[:]:
            requirements = [entry['logical-name'] for entry in rule.get('requires', [])]
            if any(name not in providers for name in requirements):
                raise RuntimeError('Missing module provider.')
            if not all(providers[name] in done for name in requirements):
                continue
            item = by_output[rule['primary-output']]
            maps = ['-fmodule-file='+name+'='+str(pcm_by_name[name]) for name in requirements]
            if rule.get('provides'):
                name = rule['provides'][0]['logical-name']
                pcm = build/(name+'.pcm')
                run([cxx, *flags, *maps, '--precompile', item['file'], '-o', pcm])
                run([cxx, *flags, '-c', pcm, '-o', item['output']])
                pcm_by_name[name] = pcm
            else:
                run([cxx, *flags, *maps, '-c', item['file'], '-o', item['output']])
            order.append(Path(item['file']).name)
            done.add(rule['primary-output']); pending.remove(rule); progress = True
        if not progress:
            raise RuntimeError('Cycle or unresolved dependency in module graph.')
    (build/'build-order.json').write_text(json.dumps(order, indent=2)+'\n')
    pcm = pcm_by_name['wwl.measurement']
    module_map = '-fmodule-file=wwl.measurement='+str(pcm)
    interface_obj, implementation_obj, importer_obj = [build/(name+'.o') for name in units]
    run([cxx, *flags, importer_obj, interface_obj, implementation_obj, library, '-o', build/'module_consumer'])
    run([cxx, *flags, here/'header_consumer.cpp', library, '-o', build/'header_consumer'])
    cases = {'reference': '2 4 6 8\n', 'new-input': '1 3 5 7\n', 'empty': '', 'invalid': '2 bad 6\n'}
    results = {}
    for name, content in cases.items():
        path = build/(name+'.txt'); path.write_text(content)
        expected = 2 if name == 'invalid' else 0
        a = run([build/'module_consumer', path], expected=expected)
        b = run([build/'header_consumer', path], expected=expected)
        if (a.returncode, a.stdout, a.stderr) != (b.returncode, b.stdout, b.stderr):
            raise RuntimeError('Header/module result mismatch: ' + name)
        (build/(name+'.stdout')).write_text(a.stdout)
        (build/(name+'.stderr')).write_text(a.stderr)
        results[name] = {'exit': a.returncode, 'equal': True}
        if name == 'reference' and a.stdout != (component/'data/report-reference.txt').read_text():
            raise RuntimeError('Published reference report mismatch.')
    if 'mean_mV=2 ' not in (build/'new-input.stdout').read_text() or 'mean_mV=6 ' not in (build/'new-input.stdout').read_text():
        raise RuntimeError('New input means must be 2,4,6 mV.')
    run([cxx, *flags, module_map, here/'type_identity.cpp', interface_obj, implementation_obj, library, '-o', build/'type_identity'])
    run([build/'type_identity'])
    rejected = {}
    def reject(name, command, pattern):
        result = run(command, expected=1, pattern=pattern)
        (build/(name+'.diagnostic')).write_text(result.stdout+result.stderr)
        rejected[name] = {'exit': result.returncode, 'diagnostic_contains': pattern}
    reject('missing-bmi', [cxx, *flags, '-c', here/'importer.cpp', '-o', build/'bad.o'], "module 'wwl.measurement' not found")
    reject('not-exported', [cxx, *flags, module_map, '-c', here/'failures/not_exported.cpp', '-o', build/'bad.o'], 'CommandOptions')
    reject('temporary-borrow', [cxx, *flags, module_map, '-c', here/'failures/temporary_borrow.cpp', '-o', build/'bad.o'], 'deleted')
    reject('missing-module-objects', [cxx, *flags, importer_obj, library, '-o', build/'bad'], 'interface_revision')
    reject('missing-legacy-library', [cxx, *flags, importer_obj, interface_obj, implementation_obj, '-o', build/'bad'], 'ReportSession')
    reject('incompatible-bmi', [cxx, '-std=c++23', *flags[1:], module_map, '-c', here/'importer.cpp', '-o', build/'bad.o'], 'C++23')
    duplicates = []
    for name in ['duplicate_a', 'duplicate_b']:
        obj = build/(name+'.o'); duplicates.append(obj)
        run([cxx, *flags, module_map, '-c', here/('failures/'+name+'.cpp'), '-o', obj])
    reject('duplicate-definition', [cxx, *flags, importer_obj, interface_obj, *duplicates, library, '-o', build/'bad'], 'duplicate symbol')
    for p in originals:
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() != identities[str(p.relative_to(vault))]:
            raise RuntimeError('Original source changed during experiment: ' + str(p))
    summary = {'type_alias_identity': True, 'config': args.config, 'scanned_module': 'wwl.measurement', 'order': order,
               'cases': results, 'expected_rejections': rejected,
               'cxx': cxx, 'scanner': scanner, 'standard': 'C++20',
               'not_verified': ['CMake CXX_MODULES/Ninja path', 'cross-compiler ABI',
                                'other platforms', 'BMI distribution/install', 'Obsidian display', 'human learning']}
    (build/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    log.close()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
