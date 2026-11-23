import codeql.ucode.Markup

from UcodeMarkup::AstNode n, UcodeMarkup::FunctionExpression f
where
  n.getParent+() = f.getBody() and
  (
    n instanceof UcodeMarkup::CallExpression or
    n instanceof UcodeMarkup::MemberExpression or
    n instanceof UcodeMarkup::OptionalChain or
    n instanceof UcodeMarkup::SubscriptExpression or
    n instanceof UcodeMarkup::SpreadElement
  )
select n.getLocation().getFile().getBaseName(), n.getAPrimaryQlClass(),
  n.getLocation().getStartColumn(), n.getLocation().getEndColumn(),
  n.getParent().getAPrimaryQlClass(), n.getParentIndex()
