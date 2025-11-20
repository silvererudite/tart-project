#!/usr/bin/env python
import sys
import os
import subprocess
import yaml
import time

def get_type(a):
    if isinstance(a, str):
        return 'str'
    elif isinstance(a, bool):
        return 'bool'
    elif isinstance(a, int):
        return 'int'
    elif isinstance(a, float):
        return 'float'
    elif isinstance(a, list):
        return 'list'
    else:
        raise ValueError('Unknown type')

if __name__=="__main__":
    taskname = sys.argv[1]

    # preferable to build the cab from the docstring but they don't all adhere
    # to a consistent format (note this may produce garbage)
    try:
        # import numpy as np; np.savez({taskname}.npz, **{taskname}.parameters)
        cmd = f'help({taskname}); quit()'

        with open(taskname + '.txt', 'w') as output:
            subprocess.Popen(['casa', '--nologger', '--log2term', '--nologfile', '-c', cmd],
                            stdout=output)

        # need to wait for the above to finish
        time.sleep(10)

        f = open(taskname + '.txt', 'r')
        # find just the relevant help string in the file
        fulltxt = f.readlines()
        for i, l in enumerate(fulltxt):
            if l.find('Arguments') > 0:
                l0 = i+1
            elif l.find('Returns') > 0:
                lf = i
                break

        docs = fulltxt[l0:lf]
        x = {}
        for i, l in enumerate(docs):
            l = l.strip()[1:].strip()
            if len(l):
                # print(i, l)
                idx = l.find(':')
                if idx > -1:  # must be a keyword
                    l0 = l[0:idx].strip()
                    l1 = l[idx:].strip()[1:].strip()
                    if 'Default Value' in l0:
                        try:
                            val = eval(l1)
                            x[key]['default'] = val
                            x[key]['dtype'] = get_type(val)
                        except:
                            x[key]['default'] = l1
                            x[key]['dtype'] = 'str'
                    elif 'Allowed Values' in l0:
                        x[key]['choices'] = []
                    else:  # must be a key
                        key = l0
                        x.setdefault(key, {})
                        x[key]['info'] = l1.strip()
                else:
                    try:
                        x[key]['choices'].append(l)
                    except:
                        print(f'Check on failure at {key}')
    except:
        cmd = f'inp({taskname}); quit()'

        with open(taskname + '.txt', 'w') as output:
            subprocess.Popen(['casa', '--nologger', '--log2term', '--nologfile', '-c', cmd],
                            stdout=output)

        # need to wait for the above to finish
        time.sleep(10)

        f = open(taskname + '.txt', 'r')
        x = {}
        for i, l in enumerate(f.readlines()):
            l = l.strip()
            print(i, l)
            if len(l) == 0:
                continue
            elif not l.startswith('#'):
                ll = l.split('=')
                if len(ll) == 2:
                    l0, l1 = l.split('=')
                else:
                    l0 = ll[0]
                    l1 = ''.join(ll[1:])
                l1, l2 = l1.split('#')
                key = l0.strip()
                val = eval(l1.strip())
                docs = l2.strip()
                print(i, key, val, docs)
                x.setdefault(key, {})
                x[key]['default'] = val
                x[key]['info'] = docs
                x[key]['dtype'] = get_type(val)
            else:
                docs = l[1:].strip()
                x[key]['info'] += ' ' + docs

    f.close()
    os.remove(taskname + '.txt')

    if 'vis' in x.keys():
        x['vis']['required'] = True
        x['vis']['dtype'] = 'MS'

    with open(f'{taskname}.yaml', 'w') as out:
        yaml.dump(x, out, default_flow_style=False, sort_keys=False)





