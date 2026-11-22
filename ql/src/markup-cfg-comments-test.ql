import codeql.ucode.Markup
string parentStatus(UcodeMarkup::AstNode n) {
  exists(n.getParent()) and result = "parent" or
  not exists(n.getParent()) and result = "no-parent"
}
from UcodeMarkup::AstNode n
where n instanceof UcodeMarkup::Comment or n instanceof UcodeMarkup::DocComment
select n.getLocation().getFile().getBaseName(), n.getAPrimaryQlClass(), parentStatus(n)
