# -*- coding: utf-8 -*-

import os
import os.path as osp
import sys

check = lambda f: not f.startswith('_') and f.endswith('.py')


def autodiscover(filename, filter=None):
    if not filter:
        filter = check
    exec_lines = []
    cur_dir = osp.abspath('.')
    abspath = osp.abspath(osp.dirname(filename))
    sys.path.insert(0, abspath)
    os.chdir(abspath)

    all_modules = []
    for path, dirs, files in os.walk('.'):
        modules = [f[:-3] for f in files if check(f)]
        if not modules:
            continue
        all_modules.append(modules)

        if path == '.':
            exec_lines.append("import %s" % (','.join(modules)))
        else:
            import_path = '.'.join([x for x in path.split(os.path.sep) if x != '.'])
            exec_lines.append("from %s import %s" % (import_path, ', '.join(modules)))

    exec('\n'.join(exec_lines))

    os.chdir(cur_dir)
    sys.path.pop(0)

    return all_modules
