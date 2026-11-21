/**
 * @name Template interpolation value edge absence
 * @description Reports direct local data-flow edges from a substitution
 *              expression to its constructed template string. An empty result
 *              is required because interpolation transforms the value.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-no-value-flow
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

private predicate isTargetTemplate(TemplateString template) {
  template.getFile().getRelativePath() = "template_args.uc"
  or
  template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  template.getLocation().getStartLine() in [343, 474]
}

private predicate isTemplateInput(TemplateString template, UCODE::AstNode raw) {
  exists(TemplateSubstitution sub, TemplateSubstitutionExpression expression |
    sub.getParent() = template and
    expression = sub.getExpression() and
    raw = expression.getRawAstNode()
  )
  or
  exists(StringFragment fragment | fragment = template.getAChild() and raw = toTreeSitter(fragment))
}

from
  TemplateString template, UCODE::AstNode raw, DataFlow::ExprNode source, DataFlow::ExprNode target
where
  isTargetTemplate(template) and
  isTemplateInput(template, raw) and
  toTreeSitter(source.getExprNode().getAstNode()) = raw and
  toTreeSitter(target.getExprNode().getAstNode()) = toTreeSitter(template) and
  DataFlow::localFlowStep(source, target)
select source,
  "unexpected value-preserving substitution-to-template edge at " +
    template.getLocation().getStartLine().toString()
