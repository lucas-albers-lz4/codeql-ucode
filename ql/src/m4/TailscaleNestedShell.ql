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
 * feasibility, runtime values, or shell execution. It requires distinct source
 * lines for the supported construction steps. No row on a different outer form
 * is not a safety finding. The real source's shell_quote body was reviewed
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

/** A node sits in the sink's nearest function, in the sink's source file. */
private predicate inSinkFunction(UCODE::AstNode n, NestedShellSink sink) {
  exists(UCODE::FunctionExpression fn |
    n.getLocation().getFile() = sink.getLocation().getFile() and
    directlyInFunction(n, fn) and directlyInFunction(sink, fn)
  )
}

/** Conservative unique local name without later/alternate writes in this file. */
private predicate stableBinding(UCODE::VariableDeclarator d, NestedShellSink sink) {
  d.getLocation().getFile() = sink.getLocation().getFile() and
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
private predicate formBinding(RequestArgsAccess source, string formName, NestedShellSink sink) {
  source.getProperty().getValue() = "form_data" and
  exists(UCODE::VariableDeclarator d |
    d.getValue() = source and formName = d.getName().getValue() and
    stableBinding(d, sink) and
    inSinkFunction(source, sink) and inSinkFunction(d, sink)
  )
}

/** A field is trimmed into a named local, possibly with an empty-string fallback. */
private predicate trimmedField(string formName, string field, string valueName, NestedShellSink sink) {
  exists(UCODE::VariableDeclarator d, NamedCall trimCall, UCODE::MemberExpression read |
    d.getName().getValue() = valueName and stableBinding(d, sink) and
    trimCall.getName() = "trim" and read = trimCall.getArgument(0) and
    ident(read.getObject(), formName) and read.getProperty().getValue() = field and
    trimmedInitializer(d, trimCall) and
    inSinkFunction(d, sink) and
    d.getLocation().getStartLine() < sink.getLocation().getStartLine()
  )
}

/** A direct push carries the quoted local value into the selected array. */
private predicate pushedField(string arrayName, string valueName, string field,
                              string commandName,
                              NestedShellSink sink) {
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
    inSinkFunction(pushCall, sink) and inSinkFunction(commandDecl, sink) and
    pushCall.getLocation().getStartLine() < commandDecl.getLocation().getStartLine() and
    pushCall.getLocation().getStartLine() < sink.getLocation().getStartLine()
  )
}

private predicate arrayJoinedIntoCommand(string arrayName, string commandName, NestedShellSink sink) {
  exists(UCODE::VariableDeclarator arrayDecl, UCODE::VariableDeclarator commandDecl,
         NamedCall joinCall, UCODE::AstNode commandPrefix |
    arrayDecl.getName().getValue() = arrayName and stableBinding(arrayDecl, sink) and
    arrayDecl.getValue() instanceof UCODE::Array and
    commandDecl.getName().getValue() = commandName and stableBinding(commandDecl, sink) and
    joinCall.getName() = "join" and literal(joinCall.getArgument(0), " ") and
    ident(joinCall.getArgument(1), arrayName) and
    concatenation(commandDecl.getValue(), commandPrefix, joinCall) and
    literal(commandPrefix, "tailscale login ") and
    inSinkFunction(arrayDecl, sink) and inSinkFunction(commandDecl, sink) and
    inSinkFunction(joinCall, sink) and
    arrayDecl.getLocation().getStartLine() < commandDecl.getLocation().getStartLine() and
    commandDecl.getLocation().getStartLine() < sink.getLocation().getStartLine()
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

/** Restrict all later joins to an imported popen with the exact outer shell grammar. */
private class NestedShellSink extends NamedFsPopenCall {
  string commandName;

  NestedShellSink() { vulnerableOuterArgument(this, commandName) }

  string getCommandName() { result = commandName }
}

from RequestArgsAccess source, NestedShellSink sink, string formName,
     string arrayName, string commandName
where
  commandName = sink.getCommandName() and
  formBinding(source, formName, sink) and
  arrayJoinedIntoCommand(arrayName, commandName, sink) and
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
