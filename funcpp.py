#!/usr/bin/python

import sys, re, os, binascii

defines = {}
implicits = []
accessors = []
storage = []
exit_code = 0

def main():
    args = sys.argv
    if len(args) < 3:
        print('FunC preprocessor parameters: input.fcp (... more inputs) output.fc')
        print('     Use --ARG=VAL for custom external-defined #defines (or --ARG)')
        print('     Use - instead of output.fc for writing to stdout')

    if len(args) == 3 and args[1] == '--':
        narg = []
        with open(args[2]) as in_file:
            for full_line in in_file:
                line = full_line.strip()
                if line != '':
                    narg.append(full_line.strip())
        narg.insert(0, args[0])
        args = narg

    out_file = None
    output_file_name = args[len(args) - 1]
    if output_file_name != '-':
        out_file = open(output_file_name, "w")
    print(';;; funcpp arguments: ' + ' '.join(args[1:]), file=out_file)
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
        if exit_code != 0:
            os.unlink(output_file_name)

def process_file(file_name, out_file, raw=False):
    global exit_code
    in_comment = False
    if_stack = []
    defining = None
    definiton = []
    storing = False
    storcnt = 0
    stordef = []
    stormode = ''
    with open(file_name) as in_file:
        for full_line in in_file:
            line = full_line.rstrip()
            if defining:
                if line.lstrip() == '#end':
                    print(';;; #end', file=out_file)
                    defines[defining] = '\n'.join(definiton)
                    defining = None
                    definiton = []
                    continue
                print(';;; ' + line)
                definiton.append(line)
                continue
            if storing:
                glob = stormode == 'global'
                root = stormode == '' or glob
                key = 'storage' if root else 'struct_' + stormode
                acc_pfx = '' if root else stormode + ':'
                acc_key = acc_pfx.replace(':', '_')
                line = line.lstrip()
                if line == '#end':
                    print(';;; #end', file=out_file)
                    list_tn = []
                    list_t = []
                    list_n = []
                    for sd in stordef:
                        list_tn.append(sd[1] + ' ' + sd[0])
                        list_t.append(sd[1])
                        list_n.append(sd[0])
                    if not glob:
                        asm1, asm2 = (str(storcnt), '') if storcnt <= 15 else (str(storcnt) + ' PUSHINT', 'VAR')
                        print('tuple ' + key + '_tuple(' + ', '.join(list_tn) + ') asm "' + asm1 + ' TUPLE' + asm2 + '";', file=out_file)
                        print('(' + ', '.join(list_t) + ') ' + key + '_untuple(tuple data) asm "' + asm1 + ' UNTUPLE' + asm2 + '";', file=out_file)
                    if root:
                        print(('tuple' if not glob else '()') + ' load_data() inline_ref {', file=out_file)
                        print('    slice cs = get_data().begin_parse();', file=out_file)
                    else:
                        print('tuple unpack_' + stormode + '(slice cs) inline_ref {', file=out_file)
                    for sd in stordef:
                        st = sd[2]
                        tne = '    ' + (sd[1] + ' ' if not glob else '') + sd[0] + ' = '
                        if st == 'uint' or st == 'int':
                            print(tne + 'cs~load_' + st + '(' + sd[3] + ');', file=out_file)
                        elif st == 'cell':
                            print(tne + 'cs~load_' + ('ref' if sd[3] else 'dict') + '();', file=out_file)
                        elif st == 'gram':
                            print(tne + 'cs~load_grams();', file=out_file)
                        elif st == 'string':
                            print('    int ' + sd[0] + '_size = cs~load_uint(8);', file=out_file)
                            print(tne + 'cs~load_bits(' + sd[0] + '_size * 8);', file=out_file)
                        elif st == 'slice':
                            print('    int ' + sd[0] + '_size = cs~load_uint(10);', file=out_file)
                            print(tne + 'cs~load_bits(' + sd[0] + '_size);', file=out_file)
                    print('    cs.end_parse();', file=out_file)
                    if not glob:
                        print('    return ' + key + '_tuple(' + ', '.join(list_n) + ');', file=out_file)
                    print('}', file=out_file)
                    if root:
                        print('() store_data(tuple data) impure inline_ref {', file=out_file)
                    else:
                        print('cell pack_' + stormode + '(tuple data) impure inline_ref {', file=out_file)
                    if not glob:
                        print('    (' + ', '.join(list_tn) + ') = ' + key + '_untuple(data);', file=out_file)
                    print('    builder bld = begin_cell()', file=out_file)
                    for sd in stordef:
                        st = sd[2]
                        tne = '            .store_'
                        if st == 'uint' or st == 'int':
                            print(tne + st + '(' + sd[0] + ', ' + sd[3] + ')', file=out_file)
                        elif st == 'cell':
                            print(tne + ('ref' if sd[3] else 'dict') + '(' + sd[0] + ')', file=out_file)
                        elif st == 'gram':
                            print(tne + 'grams(' + sd[0] + ')', file=out_file)
                        elif st == 'string':
                            print(tne + 'uint(' + sd[0] + '.slice_bits() / 8, 8)', file=out_file)
                            print(tne + 'slice(' + sd[0] + ')', file=out_file)
                        elif st == 'slice':
                            print(tne + 'uint(' + sd[0] + '.slice_bits(), 10)', file=out_file)
                            print(tne + 'slice(' + sd[0] + ')', file=out_file)
                    print('    ;', file=out_file)
                    if root:
                        print('    set_data(bld.end_cell());', file=out_file)
                    else:
                        print('    return bld.end_cell();', file=out_file)
                    print('}', file=out_file)
                    storing = False
                    storcnt = 0
                    stordef = []
                    stormode = ''
                    continue
                print(';;; ' + line, file=out_file)
                rm = re.match(r'^([a-zA-Z0-9]+)\s+(.+);$', line)
                if rm is None:
                    print(';; WARNING: RX match failed!!!', file=out_file)
                    continue
                var_type, var_name = rm.groups()
                # (u?)int([0-9]+), (cell|dict|ref|xstr(ing)?), (gram|coin)s?
                # addr(ess)? -> int8 (+_wc), uint256
                # str(ing)? -> uint8 length, slice(8*length) data
                # slice -> uint10 length, slice(length) data
                tvm_type = None
                tvm_name = 'v_' + var_name if not glob else 'g_' + var_name
                rm = re.match(r'^(u?int)([0-9]+)$', var_type)
                if rm:
                    tvm_type = 'int'
                    stordef.append([tvm_name, tvm_type, rm.group(1), rm.group(2)])
                if rm is None:
                    rm = re.match(r'^(cell|ref)$', var_type)
                    if rm:
                        tvm_type = 'cell'
                        stordef.append([tvm_name, tvm_type, 'cell', True])
                if rm is None:
                    rm = re.match(r'^(dict|optref|cell\?|ref\?)$', var_type)
                    if rm:
                        tvm_type = 'cell'
                        stordef.append([tvm_name, tvm_type, 'cell', False])
                if rm is None:
                    rm = re.match(r'^(gram|coin)s?$', var_type)
                    if rm:
                        tvm_type = 'int'
                        stordef.append([tvm_name, tvm_type, 'gram'])
                if rm is None:
                    rm = re.match(r'^addr(ress)?$', var_type)
                    if rm:
                        tvm_type = '!addr'
                        stordef.append([tvm_name, 'int', 'uint', '256'])
                        stordef.append([tvm_name + '_wc', 'int', 'int', '8'])
                if rm is None:
                    rm = re.match(r'^str(ing)?$', var_type)
                    if rm:
                        tvm_type = 'slice'
                        stordef.append([tvm_name, tvm_type, 'string'])
                if rm is None:
                    rm = re.match(r'^slice$', var_type)
                    if rm:
                        tvm_type = 'slice'
                        stordef.append([tvm_name, tvm_type, 'slice'])
                if tvm_type is not None:
                    if not glob:
                        accessors.append(acc_pfx + var_name)
                        acc_type = tvm_type if tvm_type != '!addr' else 'int'
                        print(acc_type + ' _get_' + acc_key + var_name + '_(tuple data) asm "' + str(storcnt) + ' INDEX";',
                              file=out_file)
                        print('(tuple, ()) ~_set_' + acc_key + var_name + '_(tuple data, ' + acc_type + ' value) asm "' +
                              str(storcnt) + ' SETINDEX";', file=out_file)
                        storcnt += 1
                        if tvm_type == '!addr':
                            accessors.append(acc_pfx + var_name + '_wc')
                            print('int _get_' + acc_key + var_name + '_wc_(tuple data) asm "' + str(storcnt) + ' INDEX";',
                                  file=out_file)
                            print('(tuple, ()) ~_set_' + acc_key + var_name + '_wc_(tuple data, int value) asm "' +
                                  str(storcnt) + ' SETINDEX";', file=out_file)
                            storcnt += 1
                    else:
                        acc_type = tvm_type if tvm_type != '!addr' else 'int'
                        print('global ' + acc_type + ' g_' + var_name + ';', file=out_file)
                        storcnt += 1
                        if tvm_type == '!addr':
                            print('global int g_' + var_name + '_wc;', file=out_file)
                            storcnt += 1
                else:
                    print(';; Unknown type ' + var_type, file=out_file)
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
                    # print(';;; ####################' + ('#' * len(rm.group(1))) + '######', file=out_file)
                    print(';;; ##### BEGIN INCLUDE ' + rm.group(1) + ' #####', file=out_file)
                    # print(';;; ###                 ' + (' ' * len(rm.group(1))) + '   ###', file=out_file)
                    print('', file=out_file)
                    process_file(os.path.dirname(os.path.abspath(file_name)) + os.sep + rm.group(1), out_file, not file_name.endswith('.fcp'))
                    print('', file=out_file)
                    # print(';;; ###               ' + (' ' * len(rm.group(1))) + '   ###', file=out_file)
                    print(';;; ##### END INCLUDE ' + rm.group(1) + ' #####', file=out_file)
                    # print(';;; ##################' + ('#' * len(rm.group(1))) + '######', file=out_file)
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
                    defines['F_' + flag_pos] = flag_value
                    print(';;; Internal #define F_' + flag_pos + ' ' + flag_value, file=out_file)
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
                if command == 'storage':
                    storing = True
                    storcnt = 0
                    stordef = []
                    stormode = argument
                    continue
                if command == 'error':
                    print(';;; !!! Error: ' + argument, file=sys.stderr)
                    exit_code = 1
                    continue
                if command == 'dump':
                    print(';; Defines:', file=out_file)
                    for d in defines:
                        print(';;   ' + d + ' = ' + defines[d].encode('unicode_escape').decode("utf-8"), file=out_file)
                    print(';; Implicits', file=out_file)
                    for i in implicits:
                        print(';;   ' + i, file=out_file)
                    print(';; Accessors', file=out_file)
                    for a in accessors:
                        print(';;   ' + a, file=out_file)
                    print(';; Conditional stack', file=out_file)
                    print(';;   ' + ' '.join(['True' if b else 'False' for b in if_stack]), file=out_file)
                    continue
                print('WARNING: Unknown command ' + command)
                continue
            if False not in if_stack:
                print(prepend + process_line(line, append, True), file=out_file)

exts = []

def process_line(line, append='', full=False):
    changed = True
    exts.clear()
    iters = 1000
    orig = line
    while changed:
        iters -= 1
        if iters <= 0:
            print("Line rewrite error: too deep recursion, possible circular definition", file=sys.stderr)
            print("For line: " + orig, file=sys.stderr)
            exit(2)
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
            if ':' in a:
                # Context-dependent lookup
                context, index = a.split(':')
                crx, irx = re.escape(context), re.escape(index)
                # Operator setter rewrite
                oldl = newl
                newl = re.sub(r'([\w:]*)(' + crx + r')\[(' + irx + r')]\s*([\-+*|&<>^]+)=\s*([^;]+);', acwr_op_rewrite_ctx, newl)
                if oldl != newl:
                    exts.append('[~' + a + '?=]')
                # Simple setter rewrite
                oldl = newl
                newl = re.sub(r'(' + crx + r')\[(' + irx + r')]\s*=\s*([^;]+);', acwr_rewrite_ctx, newl)
                if oldl != newl:
                    exts.append('[~' + a + '=]')
                # Simple getter rewrite
                oldl = newl
                newl = re.sub(crx + r'\[' + irx + ']', context + '._get_' + a.replace(':', '_') + '_()', newl)
                if oldl != newl:
                    exts.append('[' + a + ']')
        for a in accessors:
            arx = re.escape(a)
            # Operator setter rewrite
            oldl = newl
            newl = re.sub(r'([\w:]+)\[(' + arx + r')]\s*([\-+*|&<>^]+)=\s*([^;]+);', acwr_op_rewrite, newl)
            if oldl != newl:
                exts.append('[~' + a + '?=]')
            # Simple setter rewrite
            oldl = newl
            newl = re.sub(r'\[(' + arx + r')]\s*=\s*([^;]+);', acwr_rewrite, newl)
            if oldl != newl:
                exts.append('[~' + a + '=]')
            # Simple getter rewrite
            oldl = newl
            newl = re.sub(r'\[' + arx + ']', '._get_' + a.replace(':', '_') + '_()', newl)
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
    return '~_set_' + m.group(1).replace(':', '_') + '_(' + m.group(2) + ');'

def acwr_op_rewrite(m):
    return m.group(1) + '~_set_' + m.group(2).replace(':', '_') + '_(' + m.group(1) + '._get_' \
           + m.group(2).replace(':', '_') + '_() ' + m.group(3) + ' ' + m.group(4) + ');'

def acwr_rewrite_ctx(m):
    return m.group(1) + '~_set_' + m.group(1) + '_' + m.group(2).replace(':', '_') + '_(' + m.group(3) + ');'

def acwr_op_rewrite_ctx(m):
    return m.group(1) + m.group(2) + '~_set_' + m.group(2) + '_' + m.group(3).replace(':', '_') + '_(' \
           + m.group(1) + m.group(2) + '._get_' + m.group(2) + '_' + m.group(3).replace(':', '_') + '_() ' \
           + m.group(4) + ' ' + m.group(5) + ');'

if __name__ == "__main__":
    main()
    exit(exit_code)
