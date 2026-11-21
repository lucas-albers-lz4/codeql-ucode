/**
 * @name Template substitution source-order CFG paths
 * @description Reports CFG paths from each earlier direct interpolation
 *              expression to each later one in the selected multi-part
 *              templates. Testing only.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-substitution-cfg-order
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.CFG
import codeql.ucode.controlflow.CfgNodes
private import codeql.ucode.ast.internal.AstNodes

private int substitutionPosition(TemplateString template, TemplateSubstitution sub) {
  sub.getParent() = template and
  result =
    count(TemplateSubstitution previous |
      previous.getParent() = template and
      (
        previous.getLocation().getStartLine() < sub.getLocation().getStartLine()
        or
        previous.getLocation().getStartLine() = sub.getLocation().getStartLine() and
        previous.getLocation().getStartColumn() < sub.getLocation().getStartColumn()
      )
    )
}

private predicate isTargetTemplate(TemplateString template) {
  template.getFile().getRelativePath() = "template_args.uc"
  or
  template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  template.getLocation().getStartLine() in [343, 474]
}

from
  TemplateString template, TemplateSubstitution first, TemplateSubstitution later,
  TemplateSubstitutionExpression firstExpression, TemplateSubstitutionExpression laterExpression,
  ExprCfgNode firstCfg, ExprCfgNode laterCfg
where
  isTargetTemplate(template) and
  first.getParent() = template and
  later.getParent() = template and
  substitutionPosition(template, first) < substitutionPosition(template, later) and
  firstExpression = first.getExpression() and
  laterExpression = later.getExpression() and
  toTreeSitter(firstCfg.getAstNode()) = firstExpression.getRawAstNode() and
  toTreeSitter(laterCfg.getAstNode()) = laterExpression.getRawAstNode() and
  firstCfg.getASuccessor+() = laterCfg and
  not laterCfg.getASuccessor+() = firstCfg
select firstCfg,
  "source-order CFG path " + substitutionPosition(template, first).toString() + " -> " +
    substitutionPosition(template, later).toString() + " at " +
    template.getLocation().getStartLine().toString() + " in " + template.getFile().getRelativePath()
