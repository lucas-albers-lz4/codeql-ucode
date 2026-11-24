import codeql.ucode.Markup

string fieldName(UcodeMarkup::AstNode n) {
  exists(UcodeMarkup::ExpressionTag tag | tag = n.getParent() |
    n = tag.getOpen() and result = "open"
    or
    n = tag.getChild() and result = "expression"
    or
    n = tag.getClose() and result = "close"
  )
  or
  exists(UcodeMarkup::MemberExpression member | member = n.getParent() |
    n = member.getObject() and result = "object"
    or
    n = member.getProperty() and result = "property"
    or
    n = member.getOptionalChain() and result = "optional_chain"
  )
}

string nodeField(UcodeMarkup::AstNode n) {
  result = fieldName(n)
  or
  not exists(fieldName(n)) and result = "<none>"
}

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
where
  n.getLocation().getFile().getBaseName() =
    ["plain.ut", "trim-open.ut", "trim-close.ut", "trim-both.ut", "ordinary-member.ut", "trim-member.ut"]
select n.getLocation().getFile().getBaseName(), n.getAPrimaryQlClass(), n.toString(),
  n.getLocation().getStartLine(), n.getLocation().getStartColumn(), n.getLocation().getEndLine(),
  n.getLocation().getEndColumn(), parentKind(n), parentIndex(n), nodeField(n),
  count(UcodeMarkup::AstNode other |
    other.getLocation().getFile() = n.getLocation().getFile() and
    other.getAPrimaryQlClass() = n.getAPrimaryQlClass() and
    other.getLocation().getStartLine() = n.getLocation().getStartLine() and
    other.getLocation().getStartColumn() = n.getLocation().getStartColumn() and
    other.getLocation().getEndLine() = n.getLocation().getEndLine() and
    other.getLocation().getEndColumn() = n.getLocation().getEndColumn() and
    parentKind(other) = parentKind(n) and parentIndex(other) = parentIndex(n) and
    nodeField(other) = nodeField(n)
  )
