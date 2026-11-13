/**
 * @name ParameterNode from named formals with CFG nodes
 * @description Reports ParameterNodes for named formals that have a CFG
 *              node (block-bodied functions and expression-bodied
 *              arrows), and argument-to-parameter position matches via
 *              Call.getArgument and ParameterPosition. Testing only.
 *              Not production taint and not setInitAction path_found.
 *              Call resolution is a separate smoke.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/parameter-node
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
  (
    exists(DataFlow::ParameterNode pn, Identifier id, ParameterPosition ppos, int i |
      n = pn and
      id = pn.getParameter() and
      isParameterNode(pn, _, ppos) and
      ppos.isPositional(i) and
      msg = "param " + i.toString() + ":" + id.getName() + " in " + f.getBaseName()
    )
    or
    exists(
      ArgumentNode arg, ArgumentPosition apos, DataFlow::ParameterNode pn,
      ParameterPosition ppos, int i
    |
      n = arg and
      isArgumentNode(arg, _, apos) and
      isParameterNode(pn, _, ppos) and
      parameterMatch(ppos, apos) and
      pn.getLocation().getFile() = f and
      apos.isPositional(i) and
      msg = "arg-param " + i.toString() + " in " + f.getBaseName()
    )
  )
select n, msg
