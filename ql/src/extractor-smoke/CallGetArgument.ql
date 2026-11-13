/**
 * @name Call.getArgument from extracted arguments children
 * @description Reports wrapper Call.getArgument identifier and string
 *              children. Testing only. Not ParameterNode, not
 *              argument-to-parameter flow, not production taint, and not
 *              setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/call-get-argument
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.ast.Idents
private import codeql.ucode.dataflow.internal.DataFlowDispatch

private string argumentName(Expr arg) {
  result = arg.(Identifier).getName()
  or
  result = arg.(String).getString()
}

from Call c, int i, Expr arg, string name
where
  arg = c.getArgument(i) and
  name = argumentName(arg) and
  name != "" and
  exists(ArgumentPosition apos | apos.isPositional(i)) and
  (arg.getFile().getBaseName() = "luci" or arg.getFile().getBaseName() = "ssa_pos")
select arg, i.toString() + ":" + name + " in " + arg.getFile().getBaseName()
