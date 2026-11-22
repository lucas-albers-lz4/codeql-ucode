# Bounded import and function creation ordering

This contract adds a separate, partial top-level observation graph for clean
markup roots consisting only of default imports and expression statements of
the form `identifier.property = function(simple_parameters) { body };`.
Imports are represented by one completion node; imported bindings and string
fragments are not evaluated as nodes. The assignment path visits the object
identifier, the member reference, the function creation, the assignment
completion, and the expression-statement completion. Property names and formal
parameters are not identifier-read nodes. Every edge is normal ordering, and
no exit is asserted by this partial graph. Unsupported top-level constructs,
comments, shebangs and file diagnostics suppress the entire observation graph.

Each observed function expression identifies a separate callable scope. Its
body is never traversed during creation. A callable graph is covered only when
its body contains zero or more single-binding lexical declarations initialized
by numbers; it has its own entry, initializer and declaration-completion nodes,
and normal exit. Other bodies have a scope identity but no callable graph.
The pinned `uhttpd.uc` has unsupported calls in its body, so this contract does
not mark its root or callable body as fully covered, and no whole-file CFG
coverage is claimed. The partial graph has no edge into the callable scope.

This is an explicitly bounded ordering contract based on extracted syntax; it
is not a claim about full ucode runtime semantics, import effects, identifier
resolution, data flow, output escaping, or security analysis. Calls, branches,
loops, computed or optional member references, other import/assignment forms,
and recovery remain outside this contract.
