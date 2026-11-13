/**
 * @name sameFileJumpCall ReturnValueNode jumps to OutNode
 * @description Reports OutNode for same-file identifier calls and
 *              unique same-file member-property FunctionDeclarations,
 *              and jumpStep from that declaration's ReturnValueNode to
 *              the call expression. Testing only. Not production taint
 *              and not setInitAction path_found. Call.getIdentifier
 *              stays identifier-only. Library members, imports, and
 *              builtins stay unresolved.
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
      sameFileJumpCall(call, _) and
      msg = "out " + sourceCallName(call) + " in " + f.getBaseName()
    )
    or
    exists(DataFlow::ReturnValueNode ret, OutNode o, DataFlowCall call |
      n = o and
      jumpStep(ret, o) and
      o.getCall(_) = call and
      sameFileJumpCall(call, _) and
      msg = "jump-out " + sourceCallName(call) + " in " + f.getBaseName()
    )
  )
select n, msg
