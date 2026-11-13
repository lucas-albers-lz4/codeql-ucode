/**
 * @name ParameterPosition from extracted formals
 * @description Reports positional ParameterPosition values that match
 *              FormalParameters children or a bare arrow parameter.
 *              Testing only. Not ParameterNode, not call resolution, not
 *              production taint, and not setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/parameter-position
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.TreeSitter
private import codeql.ucode.dataflow.internal.DataFlowDispatch

private string parameterName(UCODE::AstNode child) {
  result = child.(UCODE::Identifier).getValue()
  or
  result = child.(UCODE::RestElement).getChild().getValue()
}

private predicate extractedName(File f, int pos, string name) {
  exists(UCODE::FormalParameters ps, UCODE::AstNode child |
    child = ps.getChild(pos) and
    name = parameterName(child) and
    f = child.getLocation().getFile()
  )
  or
  exists(UCODE::ArrowFunction af, UCODE::Identifier id |
    id = af.getParameter() and
    pos = 0 and
    name = id.getValue() and
    f = id.getLocation().getFile()
  )
}

from File f, ParameterPosition ppos, int pos, string name
where
  ppos.isPositional(pos) and
  extractedName(f, pos, name) and
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_pos") and
  not exists(DataFlow::ParameterNode pn)
select f, pos.toString() + ":" + name + " in " + f.getBaseName()
