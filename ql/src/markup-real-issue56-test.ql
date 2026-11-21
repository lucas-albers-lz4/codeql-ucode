import codeql.ucode.Markup
from UcodeMarkup::AstNode n
where
  n.getLocation().getFile().getBaseName() = "uhttpd.uc" and
  (n instanceof UcodeMarkup::ImportStatement or n instanceof UcodeMarkup::AssignmentExpression or
   n instanceof UcodeMarkup::FunctionExpression)
select n.getAPrimaryQlClass(), n.getLocation().getStartLine(), n.getLocation().getStartColumn(),
  n.getLocation().getEndLine(), n.getLocation().getEndColumn(), n.getParent().getAPrimaryQlClass(),
  n.getParentIndex()
