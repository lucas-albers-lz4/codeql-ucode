import codeql.ucode.Markup

from UcodeMarkup::AstNode n, UcodeMarkup::FunctionExpression f
where
  n.getLocation().getFile().getBaseName() = "uhttpd.uc" and
  n.getParent+() = f.getBody() and
  (
    n instanceof UcodeMarkup::CallExpression or
    n instanceof UcodeMarkup::ExpressionStatement or
    n instanceof UcodeMarkup::LexicalDeclaration
  )
select n.getAPrimaryQlClass(), n.getLocation().getStartLine(), n.getLocation().getStartColumn(),
  n.getLocation().getEndLine(), n.getLocation().getEndColumn(), n.getParent().getAPrimaryQlClass(),
  n.getParentIndex()
