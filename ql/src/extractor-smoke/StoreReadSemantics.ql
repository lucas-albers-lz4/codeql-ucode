/**
 * @name Content store and read semantics
 * @description Tests content identities and write-only references in the SSA fixture.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/store-read-semantics
 */

import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter
private import codeql.ucode.dataflow.internal.DataFlowPrivate

private string contentLabel(DataFlow::ContentSet c) {
  exists(DataFlow::FieldContent f | c.isSingleton(f) and result = "Field[" + f.getName() + "]")
  or
  exists(DataFlow::ElementContent e | c.isSingleton(e) and result = "Element")
}

private predicate contentCaseAccess(DataFlow::Node n) {
  exists(UCODE::MemberExpression m |
    toTreeSitter(n.asExpr().getExpr()) = m and
    m.getObject().(UCODE::Identifier).getValue() = "content_case"
  )
  or
  exists(UCODE::SubscriptExpression s |
    toTreeSitter(n.asExpr().getExpr()) = s and
    s.getObject().(UCODE::Identifier).getValue() = "content_case"
  )
}

from DataFlow::Node n1, DataFlow::Node n2, DataFlow::ContentSet c, string message
where
  n2.getLocation().getFile().getBaseName() = "ssa_neg" and
  (
    readStep(n1, c, n2) and
    contentCaseAccess(n2) and
    message = "read " + contentLabel(c) + ":" + n2.getLocation().getStartLine().toString()
    or
    storeStep(n1, c, n2) and
    n2 instanceof DataFlow::ContentContainerNode and
    message = "store " + contentLabel(c) + ":" + n1.getLocation().getStartLine().toString()
  )
select n2, message
