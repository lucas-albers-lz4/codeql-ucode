import codeql.ucode.Markup
from UcodeMarkup::AstNode n
where n instanceof UcodeMarkup::Markup or n instanceof UcodeMarkup::ExpressionTag or n instanceof UcodeMarkup::Identifier
select n.getLocation().getFile().getBaseName(), n.getAPrimaryQlClass(), n.toString(), n.getLocation().getStartLine(), n.getLocation().getStartColumn()
