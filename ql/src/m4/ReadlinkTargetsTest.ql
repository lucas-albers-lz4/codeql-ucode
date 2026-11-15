/** Test-only inventory of actual call entities and their library targets. */

import ucode as ucode
import codeql.ucode.ast.internal.TreeSitter
private import codeql.ucode.dataflow.internal.DataFlowDispatch
private import codeql.ucode.ast.internal.AstNodes

from UCODE::CallExpression raw, string path, string ident, string libs
where
  path = raw.getLocation().getFile().getRelativePath() and
  ident = concat(ucode::Call c | toTreeSitter(c) = raw | c.getIdentifier().getName(), ",") and
  libs =
    concat(DataFlowCall call, DataFlowCallable target |
      toTreeSitter(call.asCall().getCall()) = raw and target = viableLibraryCallable(call)
    |
      target.asLibraryCallable(), ","
    )
select raw, path, raw.getLocation().getStartLine(), raw.getLocation().getStartColumn(),
  raw.getFunction().getAPrimaryQlClass(), ident, libs
