import codeql.ucode.AST
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
from TemplateString template, string status
where template.getFile().getRelativePath() = "usr/share/rpcd/ucode/luci" and
  template.getLocation().getStartLine() in [343, 400] and
  (exists(DataFlow::ExprNode node | toTreeSitter(node.getExprNode().getAstNode()) = toTreeSitter(template)) and status = "has ExprNode" or
   not exists(DataFlow::ExprNode node | toTreeSitter(node.getExprNode().getAstNode()) = toTreeSitter(template)) and status = "no ExprNode")
select template, template.getLocation().getStartLine(), status
