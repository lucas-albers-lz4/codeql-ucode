import codeql.ucode.Markup
from UcodeMarkup::AstNode n
where
  n.getLocation().getFile().getBaseName() = "mixed.ut" and
  (n instanceof UcodeMarkup::Markup or n instanceof UcodeMarkup::ExpressionTag or
   n instanceof UcodeMarkup::Identifier or n instanceof UcodeMarkup::TextStatement or
   n instanceof UcodeMarkup::LexicalDeclaration or n instanceof UcodeMarkup::RawText)
select n.getAPrimaryQlClass(), n.toString(), n.getLocation().getStartLine(),
  n.getLocation().getStartColumn(), n.getLocation().getEndLine(), n.getLocation().getEndColumn(),
  n.getParent().getAPrimaryQlClass(), n.getParentIndex()
