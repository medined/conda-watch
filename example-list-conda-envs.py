#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import conda
import datetime
import subprocess
import os

def parse_envs(output):
    lines = output.splitlines()
    envs = {}
    for line in lines:
        if 'envs' not in line:
            continue
        parts = line.strip().split()
        path = parts[-1]
        env_name = os.path.basename(path)
        envs[env_name] = path
    return envs

proc = subprocess.run(["conda", "env", "list"], stdout=subprocess.PIPE, text=True)
output = proc.stdout
envs = parse_envs(output)
for env in envs:
    print(env)
