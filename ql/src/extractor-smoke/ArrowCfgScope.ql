/**
 * @name Expression-bodied arrow formals have an inner CfgScope
 * @description Reports named formals of expression-bodied arrows that
 *              are Variables with a CFG node and SSA write in the
 *              expression-body CfgScope, not the enclosing function.
 *              Testing only. Not ParameterNode, not argument/parameter
 *              taint, not production taint, and not setInitAction
 *              path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/arrow-cfgscope
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.CFG
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

private predicate expressionBodiedArrow(UCODE::ArrowFunction f) {
  exists(f.getBody()) and not f.getBody() instanceof UCODE::StatementBlock
}

private predicate expressionArrowFormal(UCODE::ArrowFunction f, UCODE::Identifier id) {
  expressionBodiedArrow(f) and
  (
    id = f.getParameter()
    or
    exists(UCODE::FormalParameters ps |
      ps = f.getParameters() and
      (
        id = ps.getChild(_)
        or
        id = ps.getChild(_).(UCODE::RestElement).getChild()
      )
    )
  )
}

private AstNode canonicalBody(UCODE::ArrowFunction f) {
  expressionBodiedArrow(f) and
  toTreeSitter(result) = f.getBody() and
  not result instanceof TExpression and
  not result instanceof TPrimaryExpression and
  not result instanceof TStatement and
  not result instanceof TDeclaration
}

from Variable v, File file, UCODE::Identifier id, UCODE::ArrowFunction f, CfgNode n
where
  expressionArrowFormal(f, id) and
  v.getAstNode() = TIdentifier(id) and
  n.getAstNode() = v.getAstNode() and
  n.getScope() = canonicalBody(f) and
  not n.getScope() instanceof StatementBlock and
  exists(Ssa::WriteDefinition def | def.getSourceVariable() = v) and
  not exists(VariableWriteAccess wa | wa.getAstNode() = v.getAstNode()) and
  not exists(DataFlow::ParameterNode pn) and
  file = v.getLocation().getFile() and
  (file.getBaseName() = "ssa_pos" or file.getBaseName() = "luci") and
  exists(CfgNode body |
    body.getAstNode() = canonicalBody(f) and
    n.getASuccessor+() = body and
    n.getScope() = body.getScope()
  )
select v, v.getName() + " in " + file.getBaseName()
