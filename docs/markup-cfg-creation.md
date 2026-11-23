# Bounded import and function creation ordering

This contract adds a separate, partial top-level observation graph for clean
markup roots consisting only of default imports whose module strings contain only unescaped
string fragments, and expression statements of
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
its body contains single-binding lexical declarations initialized by numbers or
bounded calls, and expression statements containing bounded calls. A bounded
call has an identifier or simple dotted member as its callee, and zero or more
identifier or simple dotted member arguments. Optional, computed, spread,
nested and other expressions are excluded. The graph visits the callee and
arguments in extracted source order, then the call completion, followed by its
declaration or statement completion. A dotted member visits its object
identifier then its member reference; property names are not identifier nodes.
Each callable has its own entry and normal exit. Other bodies have a scope
identity but no callable graph. This is a syntactic source-order contract; it
does not assert runtime evaluation or exceptional behavior.

The pinned `uhttpd.uc` callable is covered by this bounded graph. Its top-level
creation observation is separate, and no whole-file CFG coverage is claimed.
The partial graph has no edge into the callable scope.

This is an explicitly bounded ordering contract based on extracted syntax; it
is not a claim about full ucode runtime semantics, import effects, identifier
resolution, data flow, output escaping, or security analysis. Escaped import strings, other calls, branches,
loops, computed or optional member references, other import/assignment forms,
and recovery remain outside this contract.
