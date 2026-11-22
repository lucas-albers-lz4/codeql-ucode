import codeql.ucode.Markup

string parentKind(UcodeMarkup::AstNode n) {
  result = n.getParent().getAPrimaryQlClass()
  or
  not exists(n.getParent()) and result = "<root>"
}

int idx(UcodeMarkup::AstNode n) {
  result = n.getParentIndex()
  or
  not exists(n.getParent()) and result = -1
}

from UcodeMarkup::AstNode n
where
  n.getLocation().getFile().getBaseName() = ["supported.ut", "uhttpd.uc"] and
  not exists(UcodeMarkup::FunctionExpression f | n.getParent+() = f.getBody()) and
  (
    n instanceof UcodeMarkup::Markup or
    n instanceof UcodeMarkup::ImportStatement or
    n instanceof UcodeMarkup::ImportClause or
    n instanceof UcodeMarkup::String or
    n instanceof UcodeMarkup::StringFragment or
    n instanceof UcodeMarkup::ExpressionStatement or
    n instanceof UcodeMarkup::AssignmentExpression or
    n instanceof UcodeMarkup::MemberExpression or
    n instanceof UcodeMarkup::Identifier or
    n instanceof UcodeMarkup::PropertyIdentifier or
    n instanceof UcodeMarkup::FunctionExpression or
    n instanceof UcodeMarkup::FormalParameters or
    n instanceof UcodeMarkup::StatementBlock
  )
select n.getLocation().getFile().getBaseName(), n.getAPrimaryQlClass(), n.toString(),
  n.getLocation().getStartLine(), n.getLocation().getStartColumn(), n.getLocation().getEndLine(),
  n.getLocation().getEndColumn(), parentKind(n), idx(n)
