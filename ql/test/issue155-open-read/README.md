# Source-declared `fs.open` literal `r` fixture

The pinned, unmodified LuCI UPnP source contains `open(uci.get(...), 'r')` at
line 24. The model accepts a direct unaliased named `fs` import followed by a
direct call with an expression at argument 0, a single-fragment literal `r` at
argument 1, and at most one non-spread expression at argument 2. The third
argument accessor is raw syntax; it does not establish its value or effective
permissions. The file-wide shared guards deliberately exclude competing names,
writes, optional calls and files with extraction errors. A nonmatch is
inconclusive. No runtime binding, successful open, flow, or security conclusion
follows from this source association.

The source-first oracle in `manifest.json` pins the real source and synthetic
controls. The focused smoke checks routing and diagnostics, raw AST identities
and edges, exact model membership and argument projections, and counterfactual
controls. Its `r`/`wx` fixture contains both forms in one file and checks their
distinct call identities. No observation of the subsequent `leasefile.read`
call is asserted.
