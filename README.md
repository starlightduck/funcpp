# FunC Preprocessor
This is a python script that adds some additional preprocessing directives to FunC language.

Therefore, preprocessed files have fcp extension (kinda func++).

It is heavily built on regular expressions and therefore may bail out in some edge cases.

Preprocessor directives can optionally end with `;` but that is not required.

## Usage (script options)
To use the script supply it with names of fc (fcp) files and output file name.

Output file name can be - to output to standard output.

You can provide --ARG=VAL to provide external defines that will be applied to all following files.

## Rewrites
Some statements are rewrited into another form while processing.

`123.456$c` will turn into `123` `456000000`, and `@"NstK"` will become `0x4e73744b`.


## Supported directives

You may want to take a look at `test.fcp` for directive usage examples.

### `#include "<filename>";`
Includes the `<filename>` and embeds it into the script.

### `#define <variable> [value]`
Defines a preprocessor variable with set value that may be omitted.

### `#mldefine <variable>`
Initiates a multiline definition that ends with line containing only `#end`.

### `#undef <variable>`
Removes a defined preprocessor variable.

### `#ifdef <variable>`
Begins a conditional block that is included only if `<variable>` is defined.

### `#ifndef <variable>`
Begins a conditional block that is included only if `<variable>` is not defined.

### `#ifeq <variable> <value>`
Begins a conditional block that is included only if `<variable>` is defined and equals to `<value>`.

### `#ifneq <variable> <value>`
Begins a conditional block that is included only if `<variable>` is defined and not equals to `<value>`.

### `#ifsub <variable> <value>`
Begins a conditional block that is included only if `<variable>` is defined and contains substring `<value>`.

### `#ifnsub <variable> <value>`
Begins a conditional block that is included only if `<variable>` is defined and does not contain substring `<value>`.

### `#else`
Negates the current conditional block after this command.

### `#endif`
Ends the open conditional block.

### `#flag <value> <positive name> <negative name>`
Registers a preprocessor flag with set names.

This is equivalent to defining `F_<positive name>` set with `value`, 
and defining `implicit` functions `.<positive name>?` with code `<value> PUSHINT AND`
and `.<negative name>?` with code `<value> PUSHINT AND ISZERO`.

### `#implicit <function defintion>`
Defines an `implicit` function, that may be called without `()`.

### `#accessor <value> <name> <type>`
Creates a pair of accessors that can get and set tuple elements of defined index.
Reading accessor name is `[<name>]` and writing accessor is `[<name>] =`.
Operator writing accessor can be used for operations like `+=` in writing accessor.

### `#error Error description`
Causes compilation failure, the output file would be deleted, writes message to stderr and changes exit code.

### `#dump`
Dumps internal state of preprocessor (defines, implicits, accessors and conditional stack)

### `#storage`
Defines contract storage definition. Ends with `#end`.

Each variable starts on new line in format `type name;`.

Supported types: `(u?int)([0-9]+)`, `(cell|ref)`, `(dict|optref|cell\?|ref\?)`, `(gram|coin)s?`, 
`addr(ress)?`, `str(ing)?`, `slice`. `addr` type creates additional `<name>_wc` variable.

This will generate `storage_load`, `storage_save` functions to be used.

Using `#storage global` will load data into global variables instead of using a tuple.

If something else than `global` is provided then `arg_serialize` and `arg_unserialize` are generated.

Local storage accessors are used as `[arg:index]` or context-dependent lookup can be used such as `some_arg[index]`.
