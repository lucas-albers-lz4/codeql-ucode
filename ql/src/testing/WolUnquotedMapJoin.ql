/**
 * @name Identity callback in returned handler map and join shell command
 * @description Testing-only detection of a bounded identity callback passing request arguments to a shell command; callback name must have one declaration and one use in its source file.
 * @kind problem
 * @problem.severity recommendation
 * @tags testing
 * @id ucode/testing/wol-unquoted-map-join
 */

import codeql.ucode.AST
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.m3.Models

private predicate earlier(UCODE::AstNode a, UCODE::AstNode b) {
  a.getLocation().getFile() = b.getLocation().getFile() and
  (
    a.getLocation().getEndLine() < b.getLocation().getStartLine()
    or
    a.getLocation().getEndLine() = b.getLocation().getStartLine() and
    a.getLocation().getEndColumn() < b.getLocation().getStartColumn()
  )
}

private predicate reads(UCODE::Identifier use, AstNode declaration) {
  exists(VariableReadAccess read |
    read.getAstNode() = TIdentifier(use) and
    read.getVariable().getAstNode() = declaration and
    not exists(VariableAccess other | other != read and other.getAstNode() = read.getAstNode())
  )
}

private predicate unsharedUse(UCODE::Identifier declaration, UCODE::Identifier use) {
  declaration.getValue() = use.getValue() and
  earlier(declaration, use) and
  not exists(UCODE::Identifier other |
    other.getValue() = use.getValue() and
    other.getLocation().getFile() = use.getLocation().getFile() and
    other != declaration and
    other != use
  ) and
  not exists(UCODE::ShorthandPropertyIdentifier other |
    other.getValue() = use.getValue() and
    other.getLocation().getFile() = use.getLocation().getFile()
  ) and
  not exists(UCODE::ImportStatement other |
    other.getLocation().getFile() = use.getLocation().getFile() and
    importedLocalName(other, use.getValue())
  )
}

/** File-local source exclusion for competing builtin names and writes. */
private predicate builtinShape(NamedCall call, string name, int arity) {
  call.getName() = name and
  not exists(call.getOptionalChain()) and
  exists(call.getArgument(arity - 1)) and
  not exists(call.getArgument(arity)) and
  not exists(UCODE::SpreadElement spread | spread = call.getArgument(_)) and
  not exists(UCODE::Identifier id |
    id.getValue() = name and
    id.getLocation().getFile() = call.getLocation().getFile() and
    not id = calleeIdent(any(NamedCall other))
  ) and
  not exists(UCODE::ShorthandPropertyIdentifier id |
    id.getValue() = name and id.getLocation().getFile() = call.getLocation().getFile()
  ) and
  not exists(UCODE::ImportStatement imp |
    imp.getLocation().getFile() = call.getLocation().getFile() and importedLocalName(imp, name)
  )
}

private string staticKey(UCODE::AstNode node) {
  result = propertyName(node) or plainString(node, result)
}

private predicate plainPair(UCODE::Object object, UCODE::Pair pair) {
  pair = object.getChild(_) and
  exists(staticKey(pair.getKey())) and
  not exists(UCODE::AstNode other |
    other = object.getChild(_) and
    other != pair and
    (
      not exists(staticKey(other.(UCODE::Pair).getKey())) or
      staticKey(other.(UCODE::Pair).getKey()) = staticKey(pair.getKey())
    )
  )
}

private predicate returnedHandler(UCODE::FunctionExpression handler, UCODE::Pair method) {
  exists(
    UCODE::VariableDeclarator decl, UCODE::LexicalDeclaration lexical, UCODE::Object table,
    UCODE::Object definition, UCODE::Pair callEntry, UCODE::Pair returnedEntry,
    UCODE::Object returned, UCODE::ReturnStatement ret, UCODE::Identifier tableUse
  |
    decl.getParent() = lexical and
    lexical.getParent() instanceof UCODE::Program and
    table = decl.getValue() and
    plainPair(table, method) and
    definition = method.getValue() and
    plainPair(definition, callEntry) and
    propertyName(callEntry.getKey()) = "call" and
    handler = callEntry.getValue() and
    ret.getParent() instanceof UCODE::Program and
    returned = ret.getChild() and
    plainPair(returned, returnedEntry) and
    tableUse = returnedEntry.getValue() and
    reads(tableUse, TVariableDeclarator(decl)) and
    unsharedUse(decl.getName(), tableUse)
  )
}

private predicate handlerField(UCODE::MemberExpression field, UCODE::Identifier formal, string key) {
  exists(UCODE::MemberExpression args, UCODE::Identifier receiver |
    field.getObject() = args and
    field.getProperty().getValue() = key and
    not exists(field.getOptionalChain()) and
    not exists(args.getOptionalChain()) and
    args.getObject() = receiver and
    args.getProperty().getValue() = "args" and
    reads(receiver, TIdentifier(formal))
  )
}

private predicate stableFormal(UCODE::Identifier formal, UCODE::FunctionExpression handler) {
  handler.getParameters().getChild(0) = formal and
  not exists(handler.getParameters().getChild(1)) and
  not exists(VariableAccess access |
    access.getVariable().getAstNode() = TIdentifier(formal) and
    not exists(UCODE::MemberExpression member, UCODE::Identifier receiver |
      member.getObject() = receiver and
      member.getProperty().getValue() = "args" and
      access.getAstNode() = TIdentifier(receiver) and
      access instanceof VariableReadAccess
    )
  ) and
  not exists(UCODE::AssignmentExpression write, UCODE::Identifier receiver |
    write.getLeft().getAFieldOrChild*() = receiver and
    reads(receiver, TIdentifier(formal))
  ) and
  not exists(UCODE::AugmentedAssignmentExpression write, UCODE::Identifier receiver |
    write.getLeft().getAFieldOrChild*() = receiver and
    reads(receiver, TIdentifier(formal))
  ) and
  not exists(UCODE::UpdateExpression write, UCODE::Identifier receiver |
    write.getArgument().getAFieldOrChild*() = receiver and
    reads(receiver, TIdentifier(formal))
  ) and
  not exists(UCODE::DeleteExpression write, UCODE::Identifier receiver |
    write.getArgument().getAFieldOrChild*() = receiver and
    reads(receiver, TIdentifier(formal))
  )
}

private predicate binary(
  UCODE::BinaryExpression expr, string op, UCODE::AstNode left, UCODE::AstNode right
) {
  expr.getOperator() = op and expr.getLeft() = left and expr.getRight() = right
}

private predicate plainString(UCODE::String literal, string value) {
  literal.getChild(0).(UCODE::StringFragment).getValue() = value and
  not exists(literal.getChild(1))
}

private predicate singleQuoteBody(UCODE::AstNode expr, UCODE::Identifier param) {
  exists(
    UCODE::BinaryExpression inner, NamedCall replace, UCODE::Identifier input,
    UCODE::String opening, UCODE::String closing, UCODE::String search, UCODE::String escaped
  |
    binary(expr, "+", inner, closing) and
    binary(inner, "+", opening, replace) and
    plainString(opening, "'") and
    plainString(closing, "'") and
    builtinShape(replace, "replace", 3) and
    replace.getArgument(0) = input and
    reads(input, TIdentifier(param)) and
    replace.getArgument(1) = search and
    replace.getArgument(2) = escaped and
    plainString(search, "'") and
    escaped.getChild(0).(UCODE::StringFragment).getValue() = "'" and
    escaped.getChild(1).(UCODE::EscapeSequence).getValue() = "\\\\" and
    escaped.getChild(2).(UCODE::StringFragment).getValue() = "''" and
    not exists(escaped.getChild(3))
  )
}

private string callbackShape(UCODE::FunctionDeclaration callback) {
  exists(UCODE::Identifier param, UCODE::ReturnStatement ret, UCODE::AstNode expr |
    callback.getParameters().getChild(0) = param and
    not exists(callback.getParameters().getChild(1)) and
    ret.getParent() = callback.getBody() and
    not exists(UCODE::AstNode other |
      other = callback.getBody().getAFieldOrChild() and
      other != ret and
      not other instanceof UCODE::Comment
    ) and
    expr = ret.getChild() and
    (
      reads(expr, TIdentifier(param)) and result = "identity"
      or
      singleQuoteBody(expr, param) and result = "single-quote-body"
    )
  )
}

private predicate fixedComparison(
  UCODE::BinaryExpression cmp, UCODE::Identifier formal, string pathValue
) {
  exists(
    UCODE::MemberExpression field, UCODE::Identifier pathUse, UCODE::VariableDeclarator pathDecl,
    UCODE::LexicalDeclaration lexical, UCODE::String path
  |
    binary(cmp, "==", field, pathUse) and
    handlerField(field, formal, "name") and
    reads(pathUse, TVariableDeclarator(pathDecl)) and
    lexical = pathDecl.getParent() and
    lexical.getParent() instanceof UCODE::Program and
    not exists(VariableWriteAccess write |
      write.getVariable().getAstNode() = TVariableDeclarator(pathDecl)
    ) and
    path = pathDecl.getValue() and
    plainString(path, pathValue)
  )
}

private predicate hasFixedGuard(
  UCODE::VariableDeclarator sinkDecl, UCODE::Identifier formal, UCODE::AstNode executable
) {
  handlerField(executable, formal, "name") and
  exists(
    UCODE::IfStatement branch, UCODE::BinaryExpression disjunction, UCODE::BinaryExpression left,
    UCODE::BinaryExpression right, string first, string second
  |
    first in ["/usr/bin/etherwake", "/usr/bin/wakeonlan"] and
    second in ["/usr/bin/etherwake", "/usr/bin/wakeonlan"] and
    first != second and
    sinkDecl.getParent().getParent() = branch.getConsequence() and
    disjunction = branch.getCondition().getChild() and
    binary(disjunction, "||", left, right) and
    fixedComparison(left, formal, first) and
    fixedComparison(right, formal, second)
  )
}

from
  UCODE::FunctionExpression handler, UCODE::Pair method, UCODE::Identifier formal,
  UCODE::MemberExpression source, NamedCall mapCall, UCODE::Identifier callbackUse,
  UCODE::FunctionDeclaration callback, UCODE::VariableDeclarator parts, UCODE::Identifier partsUse,
  NamedCall joinCall, UCODE::BinaryExpression assembly, NamedFsPopenCall sink, string quoteShape,
  string guardShape, UCODE::VariableDeclarator sinkDecl, UCODE::AstNode block,
  UCODE::AstNode executable
where
  returnedHandler(handler, method) and
  stableFormal(formal, handler) and
  handlerField(source, formal, "args") and
  builtinShape(mapCall, "map", 2) and
  mapCall.getArgument(0) = source and
  mapCall.getArgument(1) = callbackUse and
  // Dynamic evaluation may replace a same-spelled callback without a
  // statically visible Identifier write. Leave such a file unclassified.
  not exists(NamedCall dynamic |
    dynamic.getLocation().getFile() = mapCall.getLocation().getFile() and
    dynamic.getName() = "eval"
  ) and
  callback.getParent() instanceof UCODE::Program and
  earlier(callback, callbackUse) and
  unsharedUse(callback.getName(), callbackUse) and
  parts.getValue() = mapCall and
  unsharedUse(parts.getName(), partsUse) and
  reads(partsUse, TVariableDeclarator(parts)) and
  parts.getParent().getParent() = block and
  sinkDecl.getParent().getParent() = block and
  earlier(parts, sinkDecl) and
  (
    block = handler.getBody()
    or
    exists(UCODE::IfStatement branch |
      branch.getParent() = handler.getBody() and block = branch.getConsequence()
    )
  ) and
  builtinShape(joinCall, "join", 2) and
  joinCall.getArgument(1) = partsUse and
  plainString(joinCall.getArgument(0), " ") and
  sinkDecl.getValue() = sink and
  sink.getArgument(0) = assembly and
  not exists(sink.getArgument(1)) and
  exists(UCODE::BinaryExpression prefix, UCODE::String separator |
    binary(assembly, "+", prefix, joinCall) and
    binary(prefix, "+", executable, separator) and
    plainString(separator, " ") and
    (handlerField(executable, formal, "name") or executable instanceof UCODE::String)
  ) and
  quoteShape = callbackShape(callback) and
  quoteShape = "identity" and
  (
    hasFixedGuard(sinkDecl, formal, executable) and guardShape = "fixed-path-comparison"
    or
    not hasFixedGuard(sinkDecl, formal, executable) and guardShape = "no-matching-comparison"
  )
select sink, "Modeled request-argument map/join assembly uses an identity callback before this source-declared fs.popen call; executable guard: " + guardShape + "."
