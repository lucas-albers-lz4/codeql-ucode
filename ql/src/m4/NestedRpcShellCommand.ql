/**
 * @name Request field in a nested double-quoted shell command
 * @description A bounded RPC handler matches a request field, trim, push, join, and a double-quoted /bin/sh -c command passed to imported fs.popen. Review bindings and both shell parsing stages.
 * @kind problem
 * @problem.severity warning
 * @id ucode/m4/nested-rpc-shell-command-candidate
 * @tags testing
 */

import codeql.ucode.m3.Models

/*
 * This is a syntactic review candidate. A matching return-table shape is not
 * runtime registration. String-name associations and source line order do not
 * prove executed data flow. Only the stated outer literal grammar is covered.
 */

private predicate ident(UCODE::AstNode n, string name) {
  n.(UCODE::Identifier).getValue() = name
}

private predicate literal(UCODE::AstNode n, string value) {
  stringLiteralValue(n.(UCODE::String)) = value
}

private predicate emptyString(UCODE::AstNode n) {
  n instanceof UCODE::String and not exists(n.(UCODE::String).getChild(_))
}

private predicate concatenation(UCODE::AstNode n, UCODE::AstNode left, UCODE::AstNode right) {
  exists(UCODE::BinaryExpression b |
    b = n and b.getOperator() = "+" and left = b.getLeft() and right = b.getRight()
  )
}

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

private predicate inSinkFunction(UCODE::AstNode n, NestedShellSink sink) {
  exists(UCODE::FunctionExpression fn |
    n.getLocation().getFile() = sink.getLocation().getFile() and
    directlyInFunction(n, fn) and directlyInFunction(sink, fn)
  )
}

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

/* The local helper returns single-quoted text with embedded quotes replaced. */
private predicate quotedHelperBody(UCODE::FunctionDeclaration def) {
  exists(UCODE::Identifier parameter, UCODE::ReturnStatement ret,
         UCODE::AstNode left, UCODE::AstNode call, UCODE::AstNode trailing,
         UCODE::AstNode leading, NamedCall replacement |
    parameter = def.getParameters().getChild(0) and
    ret.getParent() = def.getBody() and
    concatenation(ret.getChild(), left, trailing) and
    concatenation(left, leading, call) and
    literal(leading, "'") and literal(trailing, "'") and
    replacement = call and replacement.getName() = "replace" and
    ident(replacement.getArgument(0), parameter.getValue()) and
    literal(replacement.getArgument(1), "'") and
    literal(replacement.getArgument(2), "'''")
  )
}

/* Bind the exact function node installed as an assigned methods.<name>.call. */
private predicate assignedRpcCallFn(UCODE::FunctionExpression fn) {
  exists(UCODE::AssignmentExpression assignment, UCODE::MemberExpression target,
         UCODE::Object body, UCODE::Pair callPair, UCODE::Pair argsPair,
         UCODE::Identifier owner, UCODE::ReturnStatement ret,
         UCODE::VariableDeclarator table |
    target = assignment.getLeft() and owner = target.getObject() and
    table.getName().getValue() = owner.getValue() and
    table.getValue() instanceof UCODE::Object and
    table.getLocation().getFile() = assignment.getLocation().getFile() and
    not exists(UCODE::FunctionExpression inner | table.getParent*() = inner or assignment.getParent*() = inner) and
    not exists(UCODE::FunctionDeclaration inner | table.getParent*() = inner or assignment.getParent*() = inner) and
    not exists(UCODE::ArrowFunction inner | table.getParent*() = inner or assignment.getParent*() = inner) and
    not exists(UCODE::VariableDeclarator other |
      other != table and other.getLocation().getFile() = table.getLocation().getFile() and
      other.getName().getValue() = owner.getValue()
    ) and
    not exists(UCODE::AssignmentExpression write |
      write.getLocation().getFile() = table.getLocation().getFile() and
      ident(write.getLeft(), owner.getValue())
    ) and
    body = assignment.getRight() and
    callPair = body.getChild(_) and propertyName(callPair.getKey()) = "call" and
    fn = callPair.getValue() and
    argsPair = body.getChild(_) and propertyName(argsPair.getKey()) = "args" and
    ret.getLocation().getFile() = assignment.getLocation().getFile() and
    ret.getParent() instanceof UCODE::Program and
    (
      ident(ret.getChild(), owner.getValue())
      or
      exists(UCODE::Object returned, UCODE::Pair exported |
        returned = ret.getChild() and exported = returned.getChild(_) and
        ident(exported.getValue(), owner.getValue())
      )
    )
  )
}

private predicate formBinding(UCODE::MemberExpression source, string formName, NestedShellSink sink) {
  source.getProperty().getValue() = "form_data" and
  exists(UCODE::VariableDeclarator d, UCODE::FunctionExpression fn, UCODE::Identifier formal,
         UCODE::MemberExpression argsRead |
    d.getValue() = source and formName = d.getName().getValue() and
    stableBinding(d, sink) and inSinkFunction(source, sink) and inSinkFunction(d, sink) and
    assignedRpcCallFn(fn) and directlyInFunction(sink, fn) and directlyInFunction(source, fn) and
    formal = fn.getParameters().getChild(_) and
    argsRead = source.getObject() and argsRead.getProperty().getValue() = "args" and
    ident(argsRead.getObject(), formal.getValue()) and
    not exists(UCODE::VariableDeclarator shadow |
      shadow.getParent*() = fn and shadow.getName().getValue() = formal.getValue()
    ) and
    not exists(UCODE::AssignmentExpression write |
      write.getParent*() = fn and ident(write.getLeft(), formal.getValue())
    ) and
    not exists(UCODE::AugmentedAssignmentExpression write |
      write.getParent*() = fn and ident(write.getLeft(), formal.getValue())
    ) and
    not exists(UCODE::UpdateExpression write |
      write.getParent*() = fn and ident(write.getArgument(), formal.getValue())
    ) and
    not exists(UCODE::CatchClause shadow |
      shadow.getParent*() = fn and shadow.getParameter().getValue() = formal.getValue()
    )
  )
}

private predicate trimmedField(string formName, string valueName, NestedShellSink sink) {
  exists(UCODE::VariableDeclarator d, NamedCall trimCall, UCODE::MemberExpression read |
    d.getName().getValue() = valueName and stableBinding(d, sink) and
    trimCall.getName() = "trim" and read = trimCall.getArgument(0) and
    ident(read.getObject(), formName) and
    (
      d.getValue() = trimCall
      or
      exists(UCODE::BinaryExpression fallback |
        fallback = d.getValue() and fallback.getOperator() = "||" and
        fallback.getLeft() = trimCall and emptyString(fallback.getRight())
      )
    ) and
    inSinkFunction(d, sink) and d.getLocation().getStartLine() < sink.getLocation().getStartLine()
  )
}

private predicate pushedField(string arrayName, string valueName, string commandName,
                              NestedShellSink sink) {
  exists(NamedCall pushCall, NamedCall quoteCall, UCODE::FunctionDeclaration quoteDef,
         UCODE::VariableDeclarator commandDecl, UCODE::AstNode option |
    pushCall.getName() = "push" and ident(pushCall.getArgument(0), arrayName) and
    quoteCall.getName() = "shell_quote" and ident(quoteCall.getArgument(0), valueName) and
    concatenation(pushCall.getArgument(1), option, quoteCall) and
    option instanceof UCODE::String and
    stringLiteralValue(option.(UCODE::String)).regexpMatch("[-A-Za-z0-9_./ =]+") and
    sameFileCall(quoteCall, quoteDef) and quotedHelperBody(quoteDef) and
    commandDecl.getName().getValue() = commandName and inSinkFunction(commandDecl, sink) and
    inSinkFunction(pushCall, sink) and
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
    commandPrefix instanceof UCODE::String and
    stringLiteralValue(commandPrefix.(UCODE::String)).regexpMatch("[A-Za-z0-9_./ -]+") and
    inSinkFunction(arrayDecl, sink) and inSinkFunction(commandDecl, sink) and
    inSinkFunction(joinCall, sink) and
    arrayDecl.getLocation().getStartLine() < commandDecl.getLocation().getStartLine() and
    commandDecl.getLocation().getStartLine() < sink.getLocation().getStartLine()
  )
}

private predicate rawOuterArgument(NamedFsPopenCall sink, string commandName) {
  exists(UCODE::AstNode prefixAndCommand, UCODE::AstNode prefix,
         UCODE::AstNode command, UCODE::AstNode suffix |
    concatenation(sink.getArgument(0), prefixAndCommand, suffix) and
    concatenation(prefixAndCommand, prefix, command) and
    literal(prefix, "/bin/sh -c \"") and ident(command, commandName) and
    literal(suffix, " &\"")
  )
}

private class NestedShellSink extends NamedFsPopenCall {
  string commandName;
  NestedShellSink() { rawOuterArgument(this, commandName) }
  string getCommandName() { result = commandName }
}

from UCODE::MemberExpression source, NestedShellSink sink, string formName,
     string arrayName, string commandName
where
  commandName = sink.getCommandName() and formBinding(source, formName, sink) and
  arrayJoinedIntoCommand(arrayName, commandName, sink) and
  exists(string valueName |
    trimmedField(formName, valueName, sink) and
    pushedField(arrayName, valueName, commandName, sink)
  )
select sink, "A request field matches this bounded nested-shell construction; review bindings and both shell parsing stages."
