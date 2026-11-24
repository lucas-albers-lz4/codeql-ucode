/**
 * @name Direct RPC argument in an fs.popen shell word
 * @description A field of a RPC call formal appears as an unwrapped template substitution at a shell-word boundary and the template is passed directly, or through one guarded local, to imported fs.popen. Review the command and binding context.
 * @kind problem
 * @problem.severity warning
 * @id ucode/m4/direct-rpc-shell-word
 * @tags testing
 */

import codeql.ucode.m3.Models
import codeql.ucode.ast.Variables
import codeql.ucode.ast.internal.AstNodes

/** Only nodes in this method body, excluding nested callable bodies. */
private predicate directBody(UCODE::AstNode n, UCODE::FunctionExpression fn) {
  n.getParent*() = fn and
  not exists(UCODE::FunctionExpression inner | inner != fn and n.getParent*() = inner) and
  not exists(UCODE::FunctionDeclaration inner | n.getParent*() = inner) and
  not exists(UCODE::ArrowFunction inner | n.getParent*() = inner)
}

/** The actual lexical formal, with all recognized writes excluded. */
private predicate requestField(
  UCODE::MemberExpression field, UCODE::FunctionExpression fn, Variable formalVar
) {
  exists(UCODE::MemberExpression args, UCODE::Identifier receiver,
    UCODE::Identifier formal, VariableReadAccess read |
    fn = rpcCallFn(_) and
    formal = fn.getParameters().getChild(_) and
    formalVar.getAstNode() = TIdentifier(formal) and
    field.getObject() = args and args.getProperty().getValue() = "args" and
    args.getObject() = receiver and
    read.getAstNode() = TIdentifier(receiver) and read.getVariable() = formalVar and
    directBody(field, fn) and
    not exists(VariableWriteAccess write | write.getVariable() = formalVar)
  )
}

/** Raw interpolation bounded by literal whitespace, outside literal quote syntax. */
private predicate rawWord(
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

/** A direct template argument, or an exact same-binding local write. */
private predicate reachesPopen(
  UCODE::TemplateString tmpl, UCODE::FunctionExpression fn, NamedFsPopenCall sink
) {
  directBody(sink, fn) and tmpl = sink.getArgument(0)
  or
  exists(UCODE::VariableDeclarator declaration, UCODE::Identifier use,
    Variable localVar, VariableReadAccess read |
    directBody(sink, fn) and directBody(declaration, fn) and
    declaration.getValue() = tmpl and sink.getArgument(0) = use and
    read.getAstNode() = TIdentifier(use) and
    localVar = read.getVariable() and localVar.getAstNode() = TVariableDeclarator(declaration) and
    declaration.getLocation().getEndLine() < sink.getLocation().getStartLine() and
    not exists(VariableWriteAccess write | write.getVariable() = localVar)
  )
  or
  exists(UCODE::AssignmentExpression assignment, UCODE::Identifier left,
    UCODE::Identifier use, UCODE::VariableDeclarator declaration,
    Variable localVar, VariableWriteAccess write, VariableReadAccess read |
    directBody(sink, fn) and directBody(assignment, fn) and
    assignment.getRight() = tmpl and left = assignment.getLeft() and
    sink.getArgument(0) = use and
    write.getAstNode() = TIdentifier(left) and read.getAstNode() = TIdentifier(use) and
    localVar = write.getVariable() and localVar = read.getVariable() and
    localVar.getAstNode() = TVariableDeclarator(declaration) and
    not exists(declaration.getValue()) and
    assignment.getLocation().getEndLine() < sink.getLocation().getStartLine() and
    not exists(VariableWriteAccess competing |
      competing.getVariable() = localVar and competing != write and
      competing.getLocation().getStartLine() >= assignment.getLocation().getStartLine() and
      competing.getLocation().getStartLine() <= sink.getLocation().getStartLine() and
      not exists(UCODE::IfStatement branch |
        assignment.getParent*() = branch.getConsequence() and
        competing.getIdentifier().getParent*() = branch.getAlternative() and
        branch.getLocation().getEndLine() < sink.getLocation().getStartLine()
      )
    )
  )
}

from UCODE::MemberExpression source, UCODE::FunctionExpression fn,
  Variable formalVar, UCODE::TemplateString tmpl, NamedFsPopenCall sink
where
  requestField(source, fn, formalVar) and rawWord(source, tmpl) and
  directBody(tmpl, fn) and reachesPopen(tmpl, fn, sink)
select source,
  "RPC argument is directly interpolated at a shell-word boundary into a command passed to imported fs.popen at line " +
    sink.getLocation().getStartLine().toString() + ". Review the command and binding context."
