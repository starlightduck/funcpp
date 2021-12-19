#!/usr/bin/python

import sys, re, os, binascii

defines = {}
implicits = []
accessors = []
exit_code = 0

def main():
    args = sys.argv
    if len(args) < 3:
        print('FunC preprocessor parameters: input.fcp (... more inputs) output.fc')
        print('     Use --ARG=VAL for custom external-defined #defines (or --ARG)')
        print('     Use - instead of output.fc for writing to stdout')

    out_file = None
    output_file_name = args[len(args) - 1]
    if output_file_name != '-':
        out_file = open(output_file_name, "w")
    print(';;; funcpp arguments: ' + ' '.join(args[1:]))
    for arg_idx in range(1, len(args) - 1):
        arg = args[arg_idx]
        if arg[:2] == '--':
            eq_pos = arg.find('=')
            if eq_pos == -1:
                defines[arg[2:]] = ''
            else:
                var_name = arg[2:eq_pos]
                var_value = arg[eq_pos+1:]
                defines[var_name] = var_value
            continue
        process_file(os.path.abspath(arg), out_file)
    if out_file is not None:
        out_file.close()

def process_file(file_name, out_file, raw=False):
    global exit_code
    in_comment = False
    if_stack = []
    defining = None
    definiton = []
    with open(file_name) as in_file:
        for full_line in in_file:
            line = full_line.rstrip()
            if defining:
                if line.lstrip() == '#end':
                    print(';;; #end')
                    defines[defining] = '\n'.join(definiton)
                    defining = None
                    definiton = []
                    continue
                print(';;; ' + line)
                definiton.append(line)
                continue
            if raw or line[2:] == ';;':
                if False not in if_stack:
                    print(line, file=out_file)
                continue
            prepend, append = '', ''
            multiline_end = line.find('-}')
            if in_comment:
                if multiline_end == -1:
                    if False not in if_stack:
                        print(line, file=out_file)
                    continue
                else:
                    prepend = line[:multiline_end + 2]
                    line = line[multiline_end + 2:]
                    in_comment = False
            comment_start = line.find(';;')
            if comment_start != -1:
                append = line[comment_start:]
                line = line[:comment_start]
            multiline_start = line.find('{-')
            if multiline_start != -1:
                append = line[multiline_start:]
                line = line[:multiline_start]
                if multiline_end == -1:
                    in_comment = True

            if line.lstrip()[:1] == '#' and prepend == '':
                line = line.lstrip()
                if False not in if_stack:
                    print(';;; ' + line + append, file=out_file)
                if line[-1:] == ';':
                    line = line[:-1]
                space_pos = line.find(' ')
                if space_pos == -1:
                    command = line[1:]
                    argument = ''
                else:
                    command = line[1:space_pos]
                    argument = line[space_pos:].strip()
                if command in ['ifdef', 'ifndef', 'ifeq', 'ifneq', 'ifsub', 'ifnsub', 'else', 'endif']:
                    if False in if_stack:
                        print(';;; ' + line + append, file=out_file)
                if command == 'ifdef':
                    if_stack.append(argument in defines)
                    continue
                if command == 'ifndef':
                    if_stack.append(argument not in defines)
                    continue
                if command in ['ifeq', 'ifneq', 'ifsub', 'ifnsub']:
                    rm = re.match(r'^([^\s]+)\s+(.+)$', argument)
                    if rm is None:
                        print(';; WARNING: RX match failed!!!', file=out_file)
                        continue
                    if rm.group(1) not in defines:
                        if_stack.append(False)
                        continue
                    if command == 'ifeq':   if_stack.append(defines[rm.group(1)] == rm.group(2))
                    if command == 'ifneq':  if_stack.append(defines[rm.group(1)] != rm.group(2))
                    if command == 'ifsub':  if_stack.append(defines[rm.group(1)].find(rm.group(2)) != -1)
                    if command == 'ifnsub': if_stack.append(defines[rm.group(1)].find(rm.group(2)) == -1)
                    continue
                if command == 'else':
                    if_stack.append(not if_stack.pop())
                    continue
                if command == 'endif':
                    if_stack.pop()
                    continue
                if False in if_stack:
                    continue
                if command == "include":
                    rm = re.match(r'^"([^"]+)"$', argument)
                    if rm is None:
                        continue
                    print('', file=out_file)
                    print(';;; ####################' + ('#' * len(rm.group(1))) + '######', file=out_file)
                    print(';;; ##### BEGIN INCLUDE ' + rm.group(1) + ' #####', file=out_file)
                    print(';;; ###                 ' + (' ' * len(rm.group(1))) + '   ###', file=out_file)
                    print('', file=out_file)
                    process_file(os.path.dirname(os.path.abspath(file_name)) + os.sep + rm.group(1), out_file, not file_name.endswith('.fcp'))
                    print('', file=out_file)
                    print(';;; ###               ' + (' ' * len(rm.group(1))) + '   ###', file=out_file)
                    print(';;; ##### END INCLUDE ' + rm.group(1) + ' #####', file=out_file)
                    print(';;; ##################' + ('#' * len(rm.group(1))) + '######', file=out_file)
                    print('', file=out_file)
                    continue
                if command == 'define':
                    rm = re.match(r'^([^\s]+)\s+(.+)$', argument)
                    if rm is None:
                        defines[argument] = ''
                        continue
                    defines[rm.group(1)] = rm.group(2)
                    continue
                if command == 'mldefine':
                    defining = argument
                    definition = []
                    continue
                if command == 'undef':
                    del defines[argument]
                    continue
                if command == 'flag':
                    rm = re.match(r'^([0-9]+)\s+([^\s]+)\s+([^\s]+)', argument)
                    if rm is None:
                        print(';;; WARNING: RX match failed!!!', file=out_file)
                        continue
                    flag_value, flag_pos, flag_neg = rm.groups()
                    defines['Flag:' + flag_pos] = flag_value
                    print(';;; Internal #define Flag:' + flag_pos + ' ' + flag_value, file=out_file)
                    implicits.append(flag_pos + '?')
                    print('int .' + flag_pos + '?(int a)   asm "' + flag_value + ' PUSHINT AND"; ;;; Internal #implicit', file=out_file)
                    implicits.append(flag_neg + '?')
                    print('int .' + flag_neg + '?(int a)   asm "' + flag_value + ' PUSHINT AND ISZERO"; ;;; Internal #implicit', file=out_file)
                    print('', file=out_file)
                    continue
                if command == 'implicit':
                    rm = re.match(r'^.+\s+([^(]+)\(.+$', argument)
                    if rm is None:
                        print(';;; WARNING: RX match failed!!!', file=out_file)
                    else:
                        impl_fun_name = rm.group(1).lstrip('.~')
                        implicits.append(impl_fun_name)
                    print(argument + ';', file=out_file)
                    continue
                if command == 'accessor':
                    rm = re.match(r'^(\d+)\s+([^\s]+)\s+(.+)$', argument)
                    if rm is None:
                        print(';;; WARNING: RX match failed!!!', file=out_file)
                    else:
                        acc_idx, acc_name, acc_type = rm.group(1), rm.group(2), rm.group(3)
                        accessors.append(acc_name)
                        print(acc_type + ' _get_' + acc_name + '_(tuple data) asm "' + acc_idx + ' INDEX";',
                              file=out_file)
                        print('(tuple, ()) ~_set_' + acc_name + '_(tuple data, ' + acc_type + ' value) asm "' +
                              acc_idx + ' SETINDEX";', file=out_file)
                    continue
                if command == 'error':
                    print(';;; !!! Error: ' + argument, file=sys.stderr)
                    exit_code = 1
                    continue
                if command == 'dump':
                    print(';; Defines:')
                    for d in defines:
                        print(';;   ' + d + ' = ' + defines[d].encode('unicode_escape').decode("utf-8"))
                    print(';; Implicits')
                    for i in implicits:
                        print(';;   ' + i)
                    print(';; Accessors')
                    for a in accessors:
                        print(';;   ' + a)
                    print(';; Conditional stack')
                    print(';;   ' + ' '.join(['True' if b else 'False' for b in if_stack]))
                    continue
                print('WARNING: Unknown command ' + command)
                continue
            if False not in if_stack:
                print(prepend + process_line(line, append, True), file=out_file)

exts = []

def process_line(line, append='', full=False):
    changed = True
    exts.clear()
    while changed:
        newl = line
        newl = re.sub(r'([0-9\\.]+)\$c', coin_rewrite, newl)
        newl = re.sub(r'@"([^"]+)"', atstr_rewrite, newl)
        for d in defines:
            if defines[d] == '':
                continue
            oldl = newl
            # newl = newl.replace(d, defines[d])
            newl = re.sub(r'(?<![\w:])' + re.escape(d) + r'(?![\w:])', defines[d], newl)
            if oldl != newl:
                exts.append(d + '=' + defines[d].encode('unicode_escape').decode("utf-8"))
        for i in implicits:
            oldl = newl
            newl = re.sub(r'(.|~)(' + re.escape(i) + r')([\s),;])', impl_rewrite, newl)
            if oldl != newl:
                exts.append('%' + i)
        for a in accessors:
            # Operator setter rewrite
            oldl = newl
            newl = re.sub(r'([\w:]+)\[(' + re.escape(a) + r')]\s*([\-+*|&<>\^]+)=\s*([^;]+);', acwr_op_rewrite, newl)
            if oldl != newl:
                exts.append('[~' + a + '?=]')
            # Simple setter rewrite
            oldl = newl
            newl = re.sub(r'\[(' + re.escape(a) + r')]\s*=\s*([^;]+);', acwr_rewrite, newl)
            if oldl != newl:
                exts.append('[~' + a + '=]')
            # Simple getter rewrite
            oldl = newl
            newl = re.sub(r'\[' + re.escape(a) + ']', '._get_' + a + '_()', newl)
            if oldl != newl:
                exts.append('[' + a + ']')
        changed = newl != line
        if changed: line = newl
    return line + append + ((' ;;; ' + ', '.join(exts)) if full and len(exts) != 0 else '')

def coin_rewrite(m):
    nrx = str(round(float(m.group(1)) * 1000000000))
    exts.append(m.group(1) + '$c=' + nrx)
    return nrx

def atstr_rewrite(m):
    nrx = '0x' + binascii.hexlify(m.group(1).encode('ascii')).decode('ascii')
    exts.append('@"' + m.group(1) + '"=' + nrx)
    return nrx

def impl_rewrite(m):
    return m.group(1) + m.group(2) + '()' + m.group(3)

def acwr_rewrite(m):
    return '~_set_' + m.group(1) + '_(' + m.group(2) + ');'

def acwr_op_rewrite(m):
    return m.group(1) + '~_set_' + m.group(2) + '_(' + m.group(1) + '._get_' + m.group(2) + '_() ' \
           + m.group(3) + ' ' + m.group(4) + ');'

if __name__ == "__main__":
    main()
    exit(exit_code)
