import codeql.ucode.Markup

UcodeMarkup::AstNode parent(UcodeMarkup::AstNode n) {
  result = n.getParent()
  or
  n instanceof UcodeMarkup::Markup and result = n
}

int index(UcodeMarkup::AstNode n) {
  result = n.getParentIndex()
  or
  n instanceof UcodeMarkup::Markup and result = -1
}

from UcodeMarkup::AstNode n
where
  n instanceof UcodeMarkup::Markup or
  n instanceof UcodeMarkup::LexicalDeclaration or
  n instanceof UcodeMarkup::VariableDeclarator or
  n instanceof UcodeMarkup::TextStatement or
  n instanceof UcodeMarkup::ExpressionTag or
  n instanceof UcodeMarkup::Identifier or
  n instanceof UcodeMarkup::AssignmentExpression or
  n instanceof UcodeMarkup::AugmentedAssignmentExpression or
  n instanceof UcodeMarkup::UpdateExpression or
  n instanceof UcodeMarkup::DeleteExpression or
  n instanceof UcodeMarkup::MemberExpression or
  n instanceof UcodeMarkup::CallExpression or
  n instanceof UcodeMarkup::ImportSpecifier or
  n instanceof UcodeMarkup::ImportStatement or
  n instanceof UcodeMarkup::FunctionDeclaration or
  n instanceof UcodeMarkup::ExportStatement
select n, parent(n), index(n), n.getAPrimaryQlClass()
