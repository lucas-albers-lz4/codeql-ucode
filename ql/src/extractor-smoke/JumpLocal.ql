/**
 * @name jumpStep ParameterNode continues into SSA localFlowStep
 * @description Reports jumpStep into a ParameterNode that then
 *              localFlowStep+ reaches an SSA read of that formal, and
 *              ParameterNodes that locally reach an SSA read without a
 *              jump. Testing only. Not production taint and not
 *              setInitAction path_found. Unique same-file identifier
 *              and member-property FunctionDeclarations may resolve
 *              separately. jumpStep stays identifier-only.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/jump-local
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.ast.Idents
import codeql.ucode.DataFlow
private import codeql.ucode.dataflow.internal.DataFlowPrivate
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from DataFlow::Node n, File f, string msg
where
  f = n.getLocation().getFile() and
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_pos") and
  not exists(Call other | exists(other.getArguments())) and
  (
    exists(
      ArgumentNode arg, DataFlowCall call, ArgumentPosition apos,
      DataFlow::ParameterNode pn, DataFlow::SsaReadNode snk, Identifier id,
      int i
    |
      n = pn and
      jumpStep(arg, pn) and
      DataFlow::localFlowStep+(pn, snk) and
      isArgumentNode(arg, call, apos) and
      simpleIdentifierCall(call, _) and
      id = pn.getParameter() and
      snk.getDefinition().getSourceVariable().getName() = id.getName() and
      apos.isPositional(i) and
      msg =
        "jump-local " + i.toString() + ":" + id.getName() + " from " +
          call.asCall().getCall().getIdentifier().getName() + " in " +
          f.getBaseName()
    )
    or
    exists(
      DataFlow::ParameterNode pn, DataFlow::SsaReadNode snk, Identifier id,
      ParameterPosition ppos, int i
    |
      n = pn and
      id = pn.getParameter() and
      isParameterNode(pn, _, ppos) and
      ppos.isPositional(i) and
      DataFlow::localFlowStep+(pn, snk) and
      snk.getDefinition().getSourceVariable().getName() = id.getName() and
      not exists(ArgumentNode arg | jumpStep(arg, pn)) and
      msg = "param-local " + i.toString() + ":" + id.getName() + " in " +
        f.getBaseName()
    )
  )
select n, msg
