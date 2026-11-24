/**
 * @name Returned-handler argument passed through a named helper to fs.popen
 * @description A returned call-handler request field is passed as the first actual to one uniquely named same-file helper. That helper interpolates its first formal into a literal shell-word position in a template passed to imported fs.popen. Review registration and full quote context.
 * @kind problem
 * @problem.severity warning
 * @id ucode/m4/named-helper-shell-word
 * @tags testing
 */

import codeql.ucode.m3.Models

private predicate directIn(UCODE::AstNode n, UCODE::AstNode fn) {
  n.getParent*() = fn and
  not exists(UCODE::FunctionExpression inner | inner != fn and n.getParent*() = inner) and
  not exists(UCODE::FunctionDeclaration inner | inner != fn and n.getParent*() = inner) and
  not exists(UCODE::ArrowFunction inner | inner != fn and n.getParent*() = inner)
}

private predicate returnedHandler(UCODE::FunctionExpression fn) {
  exists(UCODE::VariableDeclarator table, UCODE::Object handlers,
    UCODE::Pair method, UCODE::Object methodBody, UCODE::Pair callPair,
    UCODE::ReturnStatement ret, UCODE::Object returned,
    UCODE::Pair exported, UCODE::Identifier returnedId |
    handlers = table.getValue() and method = handlers.getChild(_) and
    methodBody = method.getValue() and callPair = methodBody.getChild(_) and
    propertyName(callPair.getKey()) = "call" and fn = callPair.getValue() and
    returned = ret.getChild() and exported = returned.getChild(_) and
    returnedId = exported.getValue() and
    returnedId.getValue() = table.getName().getValue() and
    ret.getLocation().getFile() = fn.getLocation().getFile() and
    ret.getParent+() instanceof UCODE::Program and
    not exists(UCODE::FunctionExpression outer | ret.getParent*() = outer) and
    not exists(UCODE::FunctionDeclaration outer | ret.getParent*() = outer) and
    not exists(UCODE::ArrowFunction outer | ret.getParent*() = outer) and
    not exists(UCODE::VariableDeclarator other |
      other != table and other.getLocation().getFile() = table.getLocation().getFile() and
      other.getName().getValue() = table.getName().getValue()
    ) and
    not exists(UCODE::AssignmentExpression write |
      write.getLocation().getFile() = table.getLocation().getFile() and
      write.getLeft().(UCODE::Identifier).getValue() = table.getName().getValue()
    )
  )
}

private predicate stableFormal(UCODE::Identifier formal, UCODE::AstNode fn) {
  not exists(UCODE::VariableDeclarator d |
    d.getParent*() = fn and d.getName().getValue() = formal.getValue()
  ) and
  not exists(UCODE::AssignmentExpression a |
    a.getParent*() = fn and a.getLeft().(UCODE::Identifier).getValue() = formal.getValue()
  ) and
  not exists(UCODE::AugmentedAssignmentExpression a |
    a.getParent*() = fn and a.getLeft().(UCODE::Identifier).getValue() = formal.getValue()
  ) and
  not exists(UCODE::UpdateExpression u |
    u.getParent*() = fn and u.getArgument().(UCODE::Identifier).getValue() = formal.getValue()
  ) and
  not exists(UCODE::CatchClause c |
    c.getParent*() = fn and c.getParameter().getValue() = formal.getValue()
  ) and
  not exists(UCODE::FunctionDeclaration d |
    d.getParent*() = fn and d.getName().getValue() = formal.getValue()
  ) and
  not exists(UCODE::ForInStatement loop, UCODE::Identifier id |
    loop.getParent*() = fn and
    (id = loop.getVariable() or id = loop.getKey() or id = loop.getValue()) and
    id.getValue() = formal.getValue()
  ) and
  not exists(UCODE::ForInAltStatement loop, UCODE::Identifier id |
    loop.getParent*() = fn and
    (id = loop.getVariable() or id = loop.getKey() or id = loop.getValue()) and
    id.getValue() = formal.getValue()
  )
}

private predicate requestField(UCODE::MemberExpression field, UCODE::FunctionExpression fn) {
  exists(UCODE::MemberExpression args, UCODE::Identifier receiver,
    UCODE::Identifier formal |
    formal = fn.getParameters().getChild(_) and stableFormal(formal, fn) and
    field.getObject() = args and args.getProperty().getValue() = "args" and
    args.getObject() = receiver and receiver.getValue() = formal.getValue() and
    directIn(field, fn)
  )
}

private predicate uniqueHelper(UCODE::FunctionDeclaration helper, UCODE::CallExpression call,
  UCODE::FunctionExpression handler) {
  helper.getLocation().getFile() = call.getLocation().getFile() and
  helper.getParent+() instanceof UCODE::Program and
  call.getFunction().(UCODE::Identifier).getValue() = helper.getName().getValue() and
  directIn(call, handler) and
  helper.getLocation().getStartLine() < call.getLocation().getStartLine() and
  not exists(UCODE::FunctionDeclaration other |
    other != helper and other.getLocation().getFile() = helper.getLocation().getFile() and
    other.getName().getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::VariableDeclarator d |
    d.getLocation().getFile() = helper.getLocation().getFile() and
    d.getName().getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::AssignmentExpression a |
    a.getLocation().getFile() = helper.getLocation().getFile() and
    a.getLeft().(UCODE::Identifier).getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::AugmentedAssignmentExpression a |
    a.getLocation().getFile() = helper.getLocation().getFile() and
    a.getLeft().(UCODE::Identifier).getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::UpdateExpression u |
    u.getLocation().getFile() = helper.getLocation().getFile() and
    u.getArgument().(UCODE::Identifier).getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::Identifier formal |
    formal = handler.getParameters().getChild(_) and
    formal.getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::VariableDeclarator shadow |
    shadow.getParent*() = handler and
    shadow.getName().getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::CatchClause c |
    c.getParent*() = handler and c.getParameter().getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::ForInStatement loop, UCODE::Identifier id |
    loop.getParent*() = handler and
    (id = loop.getVariable() or id = loop.getKey() or id = loop.getValue()) and
    id.getValue() = helper.getName().getValue()
  ) and
  not exists(UCODE::ForInAltStatement loop, UCODE::Identifier id |
    loop.getParent*() = handler and
    (id = loop.getVariable() or id = loop.getKey() or id = loop.getValue()) and
    id.getValue() = helper.getName().getValue()
  )
}

private predicate helperWord(UCODE::FunctionDeclaration helper,
  UCODE::Identifier formal, UCODE::Identifier read,
  UCODE::TemplateString tmpl, NamedFsPopenCall sink) {
  formal = helper.getParameters().getChild(0) and stableFormal(formal, helper) and
  directIn(sink, helper) and sink.getArgument(0) = tmpl and
  directIn(tmpl, helper) and
  exists(UCODE::TemplateSubstitution sub, UCODE::StringFragment before, int i |
    sub = tmpl.getChild(i) and read = sub.getChild() and
    read.getValue() = formal.getValue() and
    before = tmpl.getChild(i - 1) and
    before.getValue().regexpMatch(".*[ \\t]") and
    (
      not exists(tmpl.getChild(i + 1))
      or
      exists(UCODE::StringFragment after |
        after = tmpl.getChild(i + 1) and after.getValue().regexpMatch("[ \\t].*"))
    ) and
    not exists(UCODE::StringFragment frag, int j |
      frag = tmpl.getChild(j) and j <= i + 1 and
      frag.getValue().regexpMatch(".*[\\\"'`\\\\].*")
    ) and
    not exists(UCODE::TemplateSubstitution earlier, int j |
      earlier = tmpl.getChild(j) and j < i
    )
  )
}

from UCODE::MemberExpression source, UCODE::FunctionExpression handler,
  UCODE::CallExpression call, UCODE::FunctionDeclaration helper,
  UCODE::Identifier formal, UCODE::Identifier read,
  UCODE::TemplateString tmpl, NamedFsPopenCall sink
where
  returnedHandler(handler) and requestField(source, handler) and
  call.getArguments().getChild(0) = source and
  uniqueHelper(helper, call, handler) and
  helperWord(helper, formal, read, tmpl, sink)
select source,
  "A returned call-handler argument reaches a raw template word in named helper " +
    helper.getName().getValue() + " and imported fs.popen at line " +
    sink.getLocation().getStartLine().toString() + ". Review registration and full quote context."
