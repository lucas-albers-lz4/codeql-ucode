/**
 * @name Template argument CFG contract controls
 * @description Checks that substitutions keep their AST/CFG identity while
 *              template construction has no value CFG node. Testing only.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-cfg-contract
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes

private predicate isTestTemplate(TemplateString template) {
  template.getFile().getRelativePath() = "template_args.uc"
  or
  template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  template.getLocation().getStartLine() in [343, 474]
}

private predicate hasExactCfgNode(TemplateSubstitutionExpression expression) {
  exists(DataFlow::ExprNode node |
    toTreeSitter(node.getExprNode().getAstNode()) = expression.getRawAstNode()
  )
}

private string exactCfgStatus(TemplateSubstitutionExpression expression) {
  result = "has exact CFG node" and hasExactCfgNode(expression)
  or
  result = "has no exact CFG node" and not hasExactCfgNode(expression)
}

from TemplateString template, TemplateSubstitution sub, TemplateSubstitutionExpression expression
where
  isTestTemplate(template) and
  sub.getParent() = template and
  expression = sub.getExpression()
select expression,
  "substitution expression " + expression.getExpressionKind() + " at " +
    expression.getLocation().getStartLine().toString() + ":" +
    expression.getLocation().getStartColumn().toString() + "-" +
    expression.getLocation().getEndLine().toString() + ":" +
    expression.getLocation().getEndColumn().toString() + " " + exactCfgStatus(expression)
