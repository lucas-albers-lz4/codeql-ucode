/**
 * @name simpleIdentifierCall ReturnValueNode jumps to OutNode
 * @description Reports OutNode for same-file identifier calls, and
 *              jumpStep from that declaration's ReturnValueNode to the
 *              call expression. Testing only. Not production taint and
 *              not setInitAction path_found. Unique same-file identifier
 *              and member-property FunctionDeclarations may resolve
 *              separately. jumpStep stays identifier-only.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/return-out
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.DataFlow
private import codeql.ucode.dataflow.internal.DataFlowPrivate
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from DataFlow::Node n, File f, string msg
where
  f = n.getLocation().getFile() and
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_pos") and
  not exists(Call other | exists(other.getArguments())) and
  (
    exists(OutNode o, DataFlowCall call |
      n = o and
      o.getCall(_) = call and
      simpleIdentifierCall(call, _) and
      msg =
        "out " + call.asCall().getCall().getIdentifier().getName() + " in " +
          f.getBaseName()
    )
    or
    exists(DataFlow::ReturnValueNode ret, OutNode o, DataFlowCall call |
      n = o and
      jumpStep(ret, o) and
      o.getCall(_) = call and
      simpleIdentifierCall(call, _) and
      msg =
        "jump-out " + call.asCall().getCall().getIdentifier().getName() + " in " +
          f.getBaseName()
    )
  )
select n, msg
