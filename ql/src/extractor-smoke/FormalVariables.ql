/**
 * @name Named formals are Variables with CFG nodes
 * @description Reports named function/arrow formals that are Variables
 *              and have a CFG node. Testing only. Not ParameterNode, not
 *              argument/parameter taint, not production taint, and not
 *              setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/formal-variables
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.CFG
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

private predicate namedFormalIdentifier(UCODE::Identifier id) {
  exists(UCODE::FormalParameters ps |
    id = ps.getChild(_)
    or
    exists(UCODE::RestElement rest | rest = ps.getChild(_) and id = rest.getChild())
  )
  or
  exists(UCODE::ArrowFunction f | id = f.getParameter())
}

from Variable v, File f, UCODE::Identifier id
where
  v.getAstNode() = TIdentifier(id) and
  namedFormalIdentifier(id) and
  f = v.getLocation().getFile() and
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_pos") and
  exists(CfgNode n | n.getAstNode() = v.getAstNode()) and
  exists(Ssa::WriteDefinition def | def.getSourceVariable() = v) and
  not exists(VariableWriteAccess wa | wa.getAstNode() = v.getAstNode()) and
  not exists(DataFlow::ParameterNode pn) and
  (
    f.getBaseName() != "ssa_pos" or v.getName() != "b"
    or
    exists(CfgNode n, CfgNode ret |
      n.getAstNode() = v.getAstNode() and
      ret.getAstNode() = TReturnStatement(_) and
      n.getASuccessor+() = ret
    )
  )
select v, v.getName() + " in " + f.getBaseName()
