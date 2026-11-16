// Experimental argument-to-formal value identities; no production flow.
import codeql.ucode.AST
import codeql.ucode.ast.Idents
import codeql.ucode.DataFlow
private import codeql.ucode.dataflow.internal.DataFlowPrivate
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from ArgumentNode arg, DataFlowCall call, ArgumentPosition apos,
  DataFlow::ParameterNode pn, ParameterPosition ppos, Identifier id, int i
where
  jumpStep(arg, pn) and
  isArgumentNode(arg, call, apos) and
  isParameterNode(pn, _, ppos) and
  apos.isPositional(i) and
  id = pn.getParameter() and
  arg.getLocation().getFile().getBaseName() = "rest.uc"
select sourceCallName(call), call.getLocation().getStartLine(), i,
  arg.getLocation().getStartLine(), arg.getLocation().getStartColumn(),
  id.getName(), pn.getLocation().getStartLine(), pn.getLocation().getStartColumn()
