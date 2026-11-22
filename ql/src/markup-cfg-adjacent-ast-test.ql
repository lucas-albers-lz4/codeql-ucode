import codeql.ucode.Markup

string parentKind(UcodeMarkup::AstNode n) {
  result = n.getParent().getAPrimaryQlClass()
  or
  not exists(n.getParent()) and result = "<root>"
}

int parentIndex(UcodeMarkup::AstNode n) {
  result = n.getParentIndex()
  or
  not exists(n.getParent()) and result = -1
}

from UcodeMarkup::AstNode n
where n.getLocation().getFile().getBaseName() = "adjacent.ut"
select n.getAPrimaryQlClass(), n.toString(), n.getLocation().getStartLine(),
  n.getLocation().getStartColumn(), n.getLocation().getEndLine(), n.getLocation().getEndColumn(),
  parentKind(n), parentIndex(n)
