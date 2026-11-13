/**
 * @name Identity arrow body identifier is an SSA read
 * @description Reports expression-bodied identity arrows (`x => x`)
 *              whose body identifier is a VariableReadAccess of the
 *              named formal, and ParameterNode localFlowStep+ to that
 *              SSA read. Testing only. Not production taint and not
 *              setInitAction path_found. Unique same-file identifier
 *              and member-property FunctionDeclarations may resolve
 *              separately.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/identity-arrow
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.ast.Idents
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter
private import codeql.ucode.dataflow.internal.DataFlowPrivate
private import codeql.ucode.dataflow.internal.DataFlowDispatch

/** Named formal of an expression-bodied arrow whose body is that identifier. */
private predicate identityArrowFormal(UCODE::ArrowFunction f, UCODE::Identifier formal) {
  exists(UCODE::Identifier body |
    body = f.getBody() and
    body.getValue() = formal.getValue() and
    (
      formal = f.getParameter()
      or
      exists(UCODE::FormalParameters ps |
        ps = f.getParameters() and
        (
          formal = ps.getChild(_)
          or
          formal = ps.getChild(_).(UCODE::RestElement).getChild()
        )
      )
    )
  )
}

from DataFlow::Node n, File f, string msg
where
  f = n.getLocation().getFile() and
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_pos") and
  not exists(Call other | exists(other.getArguments())) and
  (
    exists(UCODE::ArrowFunction arrow, UCODE::Identifier formal, Variable v |
      identityArrowFormal(arrow, formal) and
      v.getAstNode() = TIdentifier(formal) and
      n.(DataFlow::SsaDefinitionNode).getDefinition().getSourceVariable() = v and
      exists(VariableReadAccess ra |
        ra.getVariable() = v and ra.getAstNode() = TIdentifier(arrow.getBody())
      ) and
      msg = "identity-access " + v.getName() + " in " + f.getBaseName()
    )
    or
    exists(
      DataFlow::ParameterNode pn, DataFlow::SsaReadNode snk, Identifier id,
      UCODE::ArrowFunction arrow, UCODE::Identifier formal, ParameterPosition ppos,
      int i
    |
      identityArrowFormal(arrow, formal) and
      n = pn and
      id = pn.getParameter() and
      id.getName() = formal.getValue() and
      isParameterNode(pn, _, ppos) and
      ppos.isPositional(i) and
      DataFlow::localFlowStep+(pn, snk) and
      snk.getDefinition().getSourceVariable().getName() = id.getName() and
      exists(VariableReadAccess ra |
        ra.getVariable().getAstNode() = TIdentifier(formal) and
        ra.getAstNode() = TIdentifier(arrow.getBody())
      ) and
      not exists(ArgumentNode arg | jumpStep(arg, pn)) and
      msg =
        "identity-local " + i.toString() + ":" + id.getName() + " in " +
          f.getBaseName()
    )
  )
select n, msg
