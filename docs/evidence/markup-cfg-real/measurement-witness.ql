import codeql.ucode.Markup
from UcodeMarkup::AstNode n
where n instanceof UcodeMarkup::RawText or n instanceof UcodeMarkup::CallExpression or n instanceof UcodeMarkup::MemberExpression
select n.getLocation().getFile().getRelativePath(), n.getAPrimaryQlClass(), n.getLocation().getStartLine(), n.getLocation().getStartColumn(), n.getLocation().getEndLine(), n.getLocation().getEndColumn(), n.getParent().getAPrimaryQlClass(), n.getParentIndex()
