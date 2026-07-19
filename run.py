from subprocess import run
from sys import argv, executable

run([
    executable, '-m', 'pip', 'install', 
    'philh_myftp_biz==2026.07.18',
    'tree-sitter',
    'tree-sitter-kotlin'
])

from philh_myftp_biz.terminal import set_package
from philh_myftp_biz.pc import loc, Path

set_package(loc.script)

from . import java, kotlin

for file in Path(argv[1]).descendants:

    if file.ext not in ['java', 'kt']:
        continue

    print(f'Modifying:', file)

    with file.open() as f:
        content = f.read()

    match file.ext:

        case 'java':
            content = java.rewrite(content)

        case 'kt':
            content = kotlin.rewrite(content)

    with file.open('w') as f:
        f.write(content)


