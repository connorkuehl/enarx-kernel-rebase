#!/usr/bin/env python3

"""
enarx.toml:

remote = 'https://src.fedoraproject.org/rpms/kernel.git'

[[branch]]
local = 'f32-enarx'
remote = 'f32'
release = 'f32'
chroot = 'fedora-32-x86_64'

[[branch]]
local = 'f33-enarx'
remote = 'f33'
release = 'f33'
chroot = 'fedora-33-x86_64'

[[branch]]
local = 'f34-enarx'
remote = 'master'
release = 'master'
chroot = 'fedora-rawhide-x86_64'
"""


import argparse
import os
import random
import shutil
import string
import subprocess
import sys
import time
import toml


def block_file_name(local_branch):
    return f'blocked.{local_branch}'


def is_blocked(local_branch):
    return os.path.exists(block_file_name(local_branch))


def main():
    parser = argparse.ArgumentParser(description='Rebase the Enarx kernels')
    parser.add_argument('-d', '--dryrun', action='store_true')
    parser.add_argument('-c', '--cwd')
    parser.add_argument('-nr', '--norebase', action='store_true')
    parser.add_argument('-m', '--manifest')
    args = parser.parse_args()

    if args.dryrun:
        print('== dry run ==')

    tools = {
        'copr-cli': shutil.which('copr-cli'),
        'git': shutil.which('git'),
        'fedpkg': shutil.which('fedpkg'),
    }

    for name, tool in tools.items():
        if tool is None:
            print(f'missing required tool: {name}')
            sys.exit(1)

    if args.cwd is not None:
        os.chdir(args.cwd)

    config = toml.load(args.manifest)
    branches = config['branch']

    blocked_branches = list(filter(lambda b: is_blocked(b['local']), branches))

    for blocked in blocked_branches:
        name = blocked['local']
        print(f'WARNING: skipping {name} due to blocker')

    branches = list(filter(lambda b: not is_blocked(b['local']), branches))

    repo = config['copr']
    upstream = config['remote']
    for b in branches:
        chroot = b['chroot']
        local = b['local']
        release = b['release']
        remote = b['remote']
        srpm = ''

        tmp_branch = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        try:
            cmd = [tools['git'], 'checkout', '-b', tmp_branch, local]
            print(cmd)
            subprocess.run(cmd, check=True)

            cmd = [tools['git'], 'fetch', upstream, remote]
            print(cmd)
            subprocess.run(cmd, check=True)

            cmd = [tools['git'], 'rebase', 'FETCH_HEAD']
            if not args.norebase:
                print(cmd)
                subprocess.run(cmd, check=True)
            else:
                print('skipping: ' + str(cmd))

            output = ''
            cmd = [tools['fedpkg'], '--release', release, 'srpm']
            print(cmd)
            output = subprocess.check_output(cmd)
            srpm = output.splitlines()[-1].split()[-1].strip().decode('utf-8')

            ret = None
            cmd = [tools['copr-cli'], 'build', '-r', chroot, '--nowait', repo, srpm]
            print(cmd)
            if not args.dryrun:
                for timeout in [0, 60, 120, 180, 240, 300, 6000]:
                    time.sleep(timeout)
                    ret = subprocess.run(cmd).returncode
                    if ret == 0:
                        break
            if ret != 0 and not args.dryrun:
                # Make one final attempt, otherwise bail
                subprocess.run(cmd, check=True)
            
            cmd = [tools['git'], 'checkout', local]
            print(cmd)
            subprocess.run(cmd, check=True)

            cmd = [tools['git'], 'reset', '--hard', tmp_branch]
            print(cmd)
            if args.dryrun:
                subprocess.run(cmd, check=True)

            cmd = [tools['git'], 'branch', '-D', tmp_branch]
            print(cmd)
            subprocess.run(cmd, check=True)

        except subprocess.CalledProcessError:
            if args.dryrun:
                print('== dry run is tidying up ==')
                cmd = [tools['git'], 'branch', '-D', tmp_branch]
                print(cmd)
                subprocess.run(cmd)
                print('write bad branch to ' + block_file_name(local))
            else:
                with open(block_file_name(local), 'a') as blocked_file:
                    blocked_file.write(tmp_branch)
                    print(f'ERROR: see {blocked_file}')
                    pass
        
        if os.path.exists(srpm):
            print(f'rm {srpm}')
            os.remove(srpm)

        
    if args.dryrun:
        print('== end dry run ==')


if __name__ == '__main__':
    main()
