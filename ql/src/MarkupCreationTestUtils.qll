import codeql.ucode.MarkupCreationCFG

string identity(MarkupCreationCFG::Node n) {
  n.getRole() = ["entry", "exit"] and result = n.getRole()
  or
  exists(UcodeMarkup::AstNode a | a = n.getAstNode() |
    result =
      a.getAPrimaryQlClass() + ":" + a.getLocation().getStartLine().toString() + ":" +
        a.getLocation().getStartColumn().toString() + ":" + a.getLocation().getEndLine().toString() +
        ":" + a.getLocation().getEndColumn().toString() + ":" + a.getParent().getAPrimaryQlClass() +
        ":" + a.getParentIndex().toString()
  )
}

string scope(MarkupCreationCFG::Node n) {
  exists(n.getTopScope()) and result = "top"
  or
  exists(n.getCallableScope()) and
  result =
    "callable:" + n.getCallableScope().getLocation().getStartLine().toString() + ":" +
      n.getCallableScope().getLocation().getStartColumn().toString()
}

string file(MarkupCreationCFG::Node n) {
  result = n.getTopScope().getLocation().getFile().getBaseName() or
  result = n.getCallableScope().getLocation().getFile().getBaseName()
}
