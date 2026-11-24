/**
 * @name Request data in a nested, double-quoted shell command
 * @description A bounded rpcd Tailscale login shape passes request data through trim, push and join into a double-quoted /bin/sh -c argument.
 * @kind problem
 * @problem.severity warning
 * @id ucode/m4/tailscale-nested-shell-candidate
 * @tags testing
 */

import codeql.ucode.m3.Models

/*
 * Syntactic candidate only. The local helper association and body-shape check
 * do not prove runtime helper behavior. The query does not resolve aliases, branch
 * feasibility, runtime values, or shell execution. No row on a different outer
 * form is not a safety finding. The real source's shell_quote body was reviewed
 * separately against the historical parent and fix bytes.
 */

private predicate ident(UCODE::AstNode n, string name) {
  n.(UCODE::Identifier).getValue() = name
}

private predicate literal(UCODE::AstNode n, string value) {
  stringLiteralValue(n.(UCODE::String)) = value
}

/** The generated AST has no fragment for an empty quoted string. */
private predicate emptyString(UCODE::AstNode n) {
  n instanceof UCODE::String and
  not exists(n.(UCODE::String).getChild(_))
}

private predicate concatenation(UCODE::AstNode n, UCODE::AstNode left, UCODE::AstNode right) {
  exists(UCODE::BinaryExpression b |
    b = n and b.getOperator() = "+" and left = b.getLeft() and right = b.getRight()
  )
}

/** Direct `trim(field)` or `trim(field) || ''` initializer only. */
private predicate trimmedInitializer(UCODE::VariableDeclarator d, NamedCall trimCall) {
  d.getValue() = trimCall
  or
  exists(UCODE::BinaryExpression fallback |
    fallback = d.getValue() and fallback.getOperator() = "||" and
    fallback.getLeft() = trimCall and emptyString(fallback.getRight())
  )
}

/** The nearest function boundary for an expression is this function expression. */
private predicate directlyInFunction(UCODE::AstNode n, UCODE::FunctionExpression fn) {
  n.getParent*() = fn and
  not exists(UCODE::FunctionExpression inner |
    inner != fn and n.getParent*() = inner and inner.getParent+() = fn
  ) and
  not exists(UCODE::FunctionDeclaration inner |
    n.getParent*() = inner and inner.getParent+() = fn
  ) and
  not exists(UCODE::ArrowFunction inner |
    n.getParent*() = inner and inner.getParent+() = fn
  )
}

private predicate sameFunction(UCODE::AstNode a, UCODE::AstNode b) {
  exists(UCODE::FunctionExpression fn |
    directlyInFunction(a, fn) and directlyInFunction(b, fn)
  )
}

private predicate before(UCODE::AstNode a, UCODE::AstNode b) {
  a.getLocation().getFile() = b.getLocation().getFile() and
  (
    a.getLocation().getStartLine() < b.getLocation().getStartLine()
    or
    a.getLocation().getStartLine() = b.getLocation().getStartLine() and
    a.getLocation().getStartColumn() < b.getLocation().getStartColumn()
  )
}

/** Conservative unique local name without later/alternate writes in this file. */
private predicate stableBinding(UCODE::VariableDeclarator d) {
  not exists(UCODE::VariableDeclarator other |
    other != d and other.getLocation().getFile() = d.getLocation().getFile() and
    other.getName().getValue() = d.getName().getValue()
  ) and
  not exists(UCODE::AssignmentExpression write |
    write.getLocation().getFile() = d.getLocation().getFile() and
    ident(write.getLeft(), d.getName().getValue())
  ) and
  not exists(UCODE::AugmentedAssignmentExpression write |
    write.getLocation().getFile() = d.getLocation().getFile() and
    ident(write.getLeft(), d.getName().getValue())
  ) and
  not exists(UCODE::UpdateExpression write |
    write.getLocation().getFile() = d.getLocation().getFile() and
    ident(write.getArgument(), d.getName().getValue())
  )
}

/** Reviewed helper return shape; the global replace target is not resolved. */
private predicate quotedHelperBody(UCODE::FunctionDeclaration def) {
  exists(UCODE::Identifier parameter, UCODE::ReturnStatement ret,
         UCODE::AstNode left, UCODE::AstNode call, UCODE::AstNode trailing,
         UCODE::AstNode leading, NamedCall replacement |
    parameter = def.getParameters().getChild(0) and
    ret.getParent*() = def.getBody() and
    concatenation(ret.getChild(), left, trailing) and
    concatenation(left, leading, call) and
    literal(leading, "'") and literal(trailing, "'") and
    replacement = call and replacement.getName() = "replace" and
    ident(replacement.getArgument(0), parameter.getValue()) and
    literal(replacement.getArgument(1), "'") and
    replacement.getArgument(2) instanceof UCODE::String
  )
}

/** The request object is bound to a local form_data in the same RPC method. */
private predicate formBinding(RequestArgsAccess source, string formName) {
  source.getProperty().getValue() = "form_data" and
  exists(UCODE::VariableDeclarator d |
    d.getValue() = source and formName = d.getName().getValue() and
    stableBinding(d) and
    sameFunction(source, d)
  )
}

/** A field is trimmed into a named local, possibly with an empty-string fallback. */
private predicate trimmedField(string formName, string field, string valueName, NamedFsPopenCall sink) {
  exists(UCODE::VariableDeclarator d, NamedCall trimCall, UCODE::MemberExpression read |
    d.getName().getValue() = valueName and stableBinding(d) and
    trimCall.getName() = "trim" and read = trimCall.getArgument(0) and
    ident(read.getObject(), formName) and read.getProperty().getValue() = field and
    trimmedInitializer(d, trimCall) and
    sameFunction(d, sink) and before(d, sink)
  )
}

/** A direct push carries the quoted local value into the selected array. */
private predicate pushedField(string arrayName, string valueName, string field,
                              string commandName,
                              NamedFsPopenCall sink) {
  exists(NamedCall pushCall, NamedCall quoteCall, UCODE::FunctionDeclaration quoteDef,
         UCODE::VariableDeclarator commandDecl, UCODE::AstNode option |
    pushCall.getName() = "push" and
    ident(pushCall.getArgument(0), arrayName) and
    quoteCall.getName() = "shell_quote" and
    ident(quoteCall.getArgument(0), valueName) and
    concatenation(pushCall.getArgument(1), option, quoteCall) and
    (
      field = "loginserver" and literal(option, "--login-server ")
      or
      field = "loginserver_authkey" and literal(option, "--auth-key ")
    ) and
    sameFileCall(quoteCall, quoteDef) and quotedHelperBody(quoteDef) and
    commandDecl.getName().getValue() = commandName and
    sameFunction(pushCall, commandDecl) and before(pushCall, commandDecl) and
    sameFunction(pushCall, sink) and before(pushCall, sink)
  )
}

private predicate arrayJoinedIntoCommand(string arrayName, string commandName, NamedFsPopenCall sink) {
  exists(UCODE::VariableDeclarator arrayDecl, UCODE::VariableDeclarator commandDecl,
         NamedCall joinCall, UCODE::AstNode commandPrefix |
    arrayDecl.getName().getValue() = arrayName and stableBinding(arrayDecl) and
    arrayDecl.getValue() instanceof UCODE::Array and
    commandDecl.getName().getValue() = commandName and stableBinding(commandDecl) and
    joinCall.getName() = "join" and literal(joinCall.getArgument(0), " ") and
    ident(joinCall.getArgument(1), arrayName) and
    concatenation(commandDecl.getValue(), commandPrefix, joinCall) and
    literal(commandPrefix, "tailscale login ") and
    sameFunction(arrayDecl, sink) and sameFunction(commandDecl, sink) and
    sameFunction(joinCall, sink) and before(arrayDecl, commandDecl) and
    before(commandDecl, sink)
  )
}

/** The outer shell receives a double-quoted command with the joined local. */
private predicate vulnerableOuterArgument(NamedFsPopenCall sink, string commandName) {
  exists(UCODE::AstNode prefixAndCommand, UCODE::AstNode prefix,
         UCODE::AstNode command, UCODE::AstNode suffix |
    concatenation(sink.getArgument(0), prefixAndCommand, suffix) and
    concatenation(prefixAndCommand, prefix, command) and
    literal(prefix, "/bin/sh -c \"") and
    ident(command, commandName) and literal(suffix, " &\"")
  )
}

from RequestArgsAccess source, NamedFsPopenCall sink, string formName,
     string arrayName, string commandName
where
  formBinding(source, formName) and sameFunction(source, sink) and
  arrayJoinedIntoCommand(arrayName, commandName, sink) and
  vulnerableOuterArgument(sink, commandName) and
  (
    exists(string valueName |
      trimmedField(formName, "loginserver", valueName, sink) and
      pushedField(arrayName, valueName, "loginserver", commandName, sink)
    )
    or
    exists(string valueName |
      trimmedField(formName, "loginserver_authkey", valueName, sink) and
      pushedField(arrayName, valueName, "loginserver_authkey", commandName, sink)
    )
  )
select sink, "A request-derived value matches this bounded nested-shell command construction."
