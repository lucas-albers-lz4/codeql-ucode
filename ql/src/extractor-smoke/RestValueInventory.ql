// Non-vacuity controls for all calls and named parameter nodes.
import codeql.ucode.AST
import codeql.ucode.ast.Idents
import codeql.ucode.DataFlow
private import codeql.ucode.dataflow.internal.DataFlowPrivate
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from string kind, string name, int line, int col, int position
where
  exists(Call c |
    c.getLocation().getFile().getBaseName() = "rest.uc" and
    kind = "call" and name = c.getIdentifier().getName() and
    line = c.getLocation().getStartLine() and col = c.getLocation().getStartColumn() and
    position = -1
  )
  or
  exists(DataFlow::ParameterNode pn, ParameterPosition pos, Identifier id |
    pn.getLocation().getFile().getBaseName() = "rest.uc" and
    isParameterNode(pn, _, pos) and pos.isPositional(position) and
    id = pn.getParameter() and kind = "formal" and name = id.getName() and
    line = pn.getLocation().getStartLine() and col = pn.getLocation().getStartColumn()
  )
  or
  exists(ArgumentNode arg, DataFlowCall call, ArgumentPosition pos |
    arg.getLocation().getFile().getBaseName() = "rest.uc" and
    isArgumentNode(arg, call, pos) and pos.isPositional(position) and
    kind = "argument" and name = sourceCallName(call) and
    line = arg.getLocation().getStartLine() and col = arg.getLocation().getStartColumn()
  )
select kind, name, line, col, position
