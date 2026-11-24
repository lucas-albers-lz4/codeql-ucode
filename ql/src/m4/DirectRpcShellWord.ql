/**
 * @name Direct returned-handler argument in an fs.popen command
 * @description A field of a returned call-handler formal appears as a raw template substitution between literal whitespace and the template is passed directly, or through one guarded local, to imported fs.popen. Review registration, quote context, and command behavior.
 * @kind problem
 * @problem.severity warning
 * @id ucode/m4/direct-rpc-shell-word
 * @tags testing
 */

import codeql.ucode.m3.Models

private predicate directBody(UCODE::AstNode n, UCODE::FunctionExpression fn) {
  n.getParent*() = fn and
  not exists(UCODE::FunctionExpression inner | inner != fn and n.getParent*() = inner) and
  not exists(UCODE::FunctionDeclaration inner | n.getParent*() = inner) and
  not exists(UCODE::ArrowFunction inner | n.getParent*() = inner)
}

/** A top-level returned table with a direct `name: { call: function(...) }` entry. */
private predicate returnedCallHandler(UCODE::FunctionExpression fn) {
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

/** Conservative same-handler name binding; shadows or writes make the formal unknown. */
private predicate stableFormal(UCODE::Identifier formal, UCODE::FunctionExpression fn) {
  formal = fn.getParameters().getChild(_) and
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
  )
}

private predicate handlerField(UCODE::MemberExpression field, UCODE::FunctionExpression fn) {
  exists(UCODE::MemberExpression args, UCODE::Identifier receiver,
    UCODE::Identifier formal |
    stableFormal(formal, fn) and
    field.getObject() = args and args.getProperty().getValue() = "args" and
    args.getObject() = receiver and receiver.getValue() = formal.getValue() and
    directBody(field, fn)
  )
}

/** Literal boundaries; dynamic substitutions elsewhere still need human review. */
private predicate rawLiteralBoundary(
  UCODE::MemberExpression field, UCODE::TemplateString tmpl
) {
  exists(UCODE::TemplateSubstitution sub, UCODE::StringFragment before,
    UCODE::StringFragment after, int i |
    sub.getChild() = field and sub = tmpl.getChild(i) and
    before = tmpl.getChild(i - 1) and after = tmpl.getChild(i + 1) and
    before.getValue().regexpMatch(".*[ \\t]") and
    after.getValue().regexpMatch("[ \\t].*") and
    not exists(UCODE::StringFragment frag, int j |
      frag = tmpl.getChild(j) and j <= i + 1 and
      frag.getValue().regexpMatch(".*[\\\"'`\\\\].*")
    )
  )
}

private predicate uniqueLocal(UCODE::VariableDeclarator declaration,
  UCODE::FunctionExpression fn) {
  directBody(declaration, fn) and
  not exists(UCODE::VariableDeclarator other |
    other != declaration and other.getParent*() = fn and
    other.getName().getValue() = declaration.getName().getValue()
  ) and
  not exists(UCODE::FunctionDeclaration other |
    other.getParent*() = fn and other.getName().getValue() = declaration.getName().getValue()
  )
}

/** Direct sink or one conservative same-handler local. */
private predicate reachesPopen(
  UCODE::TemplateString tmpl, UCODE::FunctionExpression fn, NamedFsPopenCall sink
) {
  directBody(sink, fn) and tmpl = sink.getArgument(0)
  or
  exists(UCODE::VariableDeclarator declaration, UCODE::Identifier use |
    directBody(sink, fn) and uniqueLocal(declaration, fn) and
    declaration.getValue() = tmpl and sink.getArgument(0) = use and
    use.getValue() = declaration.getName().getValue() and
    declaration.getLocation().getEndLine() < sink.getLocation().getStartLine() and
    not exists(UCODE::AssignmentExpression write |
      write.getParent*() = fn and
      write.getLeft().(UCODE::Identifier).getValue() = use.getValue()
    ) and
    not exists(UCODE::AugmentedAssignmentExpression write |
      write.getParent*() = fn and
      write.getLeft().(UCODE::Identifier).getValue() = use.getValue()
    )
  )
  or
  exists(UCODE::AssignmentExpression assignment, UCODE::Identifier left,
    UCODE::Identifier use, UCODE::VariableDeclarator declaration |
    directBody(sink, fn) and directBody(assignment, fn) and
    assignment.getRight() = tmpl and left = assignment.getLeft() and
    sink.getArgument(0) = use and
    uniqueLocal(declaration, fn) and not exists(declaration.getValue()) and
    left.getValue() = declaration.getName().getValue() and
    use.getValue() = left.getValue() and
    assignment.getLocation().getEndLine() < sink.getLocation().getStartLine() and
    not exists(UCODE::IfStatement branch |
      assignment.getParent*() = branch.getConsequence() and
      sink.getParent*() = branch.getAlternative()
    ) and
    not exists(UCODE::AssignmentExpression competing |
      competing != assignment and competing.getParent*() = fn and
      competing.getLeft().(UCODE::Identifier).getValue() = left.getValue() and
      competing.getLocation().getStartLine() >= assignment.getLocation().getStartLine() and
      competing.getLocation().getStartLine() <= sink.getLocation().getStartLine() and
      not exists(UCODE::IfStatement branch |
        assignment.getParent*() = branch.getConsequence() and
        competing.getParent*() = branch.getAlternative() and
        branch.getLocation().getEndLine() < sink.getLocation().getStartLine()
      )
    ) and
    not exists(UCODE::AugmentedAssignmentExpression competing |
      competing.getParent*() = fn and
      competing.getLeft().(UCODE::Identifier).getValue() = left.getValue() and
      competing.getLocation().getStartLine() >= assignment.getLocation().getStartLine() and
      competing.getLocation().getStartLine() <= sink.getLocation().getStartLine()
    )
  )
}

from NamedFsPopenCall sink, UCODE::FunctionExpression fn,
  UCODE::TemplateString tmpl, UCODE::MemberExpression source
where
  directBody(sink, fn) and returnedCallHandler(fn) and
  sink.getLocation().getFile() = fn.getLocation().getFile() and
  reachesPopen(tmpl, fn, sink) and
  source.getLocation().getFile() = sink.getLocation().getFile() and
  handlerField(source, fn) and rawLiteralBoundary(source, tmpl) and
  directBody(tmpl, fn)
select source,
  "A returned call-handler argument is directly interpolated between literal whitespace into a command passed to imported fs.popen at line " +
    sink.getLocation().getStartLine().toString() + ". Review registration and the full quote context."
