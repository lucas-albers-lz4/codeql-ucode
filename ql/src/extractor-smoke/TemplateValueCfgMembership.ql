/**
 * @name Constructed template value CFG membership should be absent
 * @description Reports a constructed template string represented as a
 *              data-flow expression node. An empty result is required.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/template-value-cfg-membership
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes

from TemplateString template, DataFlow::ExprNode node
where
  (
    template.getFile().getRelativePath() = "template_args.uc"
    or
    template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
    template.getLocation().getStartLine() in [343, 474]
  ) and
  toTreeSitter(node.getExprNode().getAstNode()) = toTreeSitter(template)
select template,
  "template unexpectedly has CFG expression node at " +
    template.getLocation().getStartLine().toString() + ":" +
    template.getLocation().getStartColumn().toString()
