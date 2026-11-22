import codeql.ucode.MarkupCFG

string identity(MarkupCFG::Node n) {
  result = n.getRole() and n.getRole() = ["entry", "exit"]
  or
  exists(UcodeMarkup::AstNode a | a = n.getAstNode() |
    result =
      a.getAPrimaryQlClass() + ":" + a.getLocation().getStartLine().toString() + ":" +
        a.getLocation().getStartColumn().toString() + ":" + a.getLocation().getEndLine().toString() +
        ":" + a.getLocation().getEndColumn().toString() + ":" + a.getParent().getAPrimaryQlClass() +
        ":" + a.getParentIndex().toString()
  )
}
