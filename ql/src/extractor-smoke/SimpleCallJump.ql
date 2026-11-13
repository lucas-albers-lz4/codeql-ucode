/**
 * @name jumpStep from same-file identifier and unique member Call.getArgument
 * @description Reports jumpStep from Call.getArgument into a
 *              ParameterNode when the call is a same-file identifier
 *              function declaration or a unique same-file
 *              member-property FunctionDeclaration. Testing only. Not
 *              production taint and not setInitAction path_found.
 *              Call.getIdentifier stays identifier-only. Library
 *              members, imports, and builtins stay unresolved.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/simple-call-jump
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
  exists(
    ArgumentNode arg, DataFlowCall call, ArgumentPosition apos,
    DataFlow::ParameterNode pn, ParameterPosition ppos, Identifier id, int i
  |
    n = pn and
    jumpStep(arg, pn) and
    isArgumentNode(arg, call, apos) and
    isParameterNode(pn, _, ppos) and
    parameterMatch(ppos, apos) and
    sameFileJumpCall(call, _) and
    id = pn.getParameter() and
    apos.isPositional(i) and
    msg =
      "jump-param " + i.toString() + ":" + id.getName() + " from " +
        sourceCallName(call) + " in " + f.getBaseName()
  )
select n, msg
