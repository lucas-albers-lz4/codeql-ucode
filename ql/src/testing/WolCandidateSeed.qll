private import codeql.files.FileSystem
private import codeql.ucode.ast.internal.TreeSitter
private import codeql.ucode.m3.Models

/** Necessary source-shape superset; not a binding or security assertion. */
predicate candidateSite(UCODE::VariableDeclarator parts, NamedFsPopenCall sink) {
  exists(
    UCODE::FunctionExpression handler, UCODE::AstNode block,
    UCODE::VariableDeclarator sinkDecl, NamedCall mapCall, NamedCall joinCall,
    UCODE::Identifier partsUse, UCODE::BinaryExpression assembly, UCODE::BinaryExpression prefix,
    UCODE::String separator, UCODE::AstNode executable
  |
    mapCall.getName() = "map" and mapCall.getArgument(0) instanceof UCODE::MemberExpression and
    mapCall.getArgument(1) instanceof UCODE::Identifier and parts.getValue() = mapCall and
    parts.getParent().getParent() = block and sinkDecl.getParent().getParent() = block and
    (block = handler.getBody() or exists(UCODE::IfStatement branch |
      branch.getParent() = handler.getBody() and block = branch.getConsequence())) and
    joinCall.getName() = "join" and joinCall.getArgument(1) = partsUse and
    partsUse.getValue() = parts.getName().getValue() and
    sinkDecl.getValue() = sink and sink.getArgument(0) = assembly and
    assembly.getOperator() = "+" and assembly.getLeft() = prefix and assembly.getRight() = joinCall and
    prefix.getOperator() = "+" and prefix.getLeft() = executable and prefix.getRight() = separator
  )
}

/** Files in which every same-file declaration/access remains in scope. */
predicate candidateFile(File file) {
  exists(UCODE::VariableDeclarator parts, NamedFsPopenCall sink |
    candidateSite(parts, sink) and file = sink.getLocation().getFile()
  )
}
