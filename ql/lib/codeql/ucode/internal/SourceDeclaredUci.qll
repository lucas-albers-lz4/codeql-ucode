/** Conservative source attribution for a narrow cursor commit call shape. */
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.Variables
import codeql.ucode.Diagnostics

private predicate before(UCODE::AstNode a, UCODE::AstNode b) {
  a.getLocation().getFile() = b.getLocation().getFile() and
  (a.getLocation().getEndLine() < b.getLocation().getStartLine() or
   a.getLocation().getEndLine() = b.getLocation().getStartLine() and
   a.getLocation().getEndColumn() < b.getLocation().getStartColumn())
}

private predicate functionNode(UCODE::AstNode n) {
  n instanceof UCODE::FunctionExpression or n instanceof UCODE::FunctionDeclaration or
  n instanceof UCODE::ArrowFunction
}

private predicate nearestFunction(UCODE::AstNode n, UCODE::AstNode f) {
  n.getParent+() = f and functionNode(f) and
  not exists(UCODE::AstNode inner |
    functionNode(inner) and n.getParent+() = inner and inner.getParent+() = f
  )
}

private UCODE::Identifier importBinding(UCODE::ImportStatement imp) {
  exists(UCODE::ImportSpecifier spec |
    spec = imp.getClause().getNamed().getChild(_) and
    (result = spec.getAlias() or not exists(spec.getAlias()) and result = spec.getName())
  )
  or result = imp.getClause().getDefault()
  or result = imp.getClause().getNamespace().getChild()
}

private predicate write(UCODE::AstNode target) {
  exists(UCODE::ParenthesizedExpression p | p.getChild() = target and write(p)) or
  exists(UCODE::AssignmentExpression a | a.getLeft() = target) or
  exists(UCODE::AugmentedAssignmentExpression a | a.getLeft() = target) or
  exists(UCODE::UpdateExpression u | u.getArgument() = target) or
  exists(UCODE::DeleteExpression d | d.getArgument() = target) or
  exists(UCODE::ForInStatement f | not exists(f.getKind()) and
    (f.getVariable() = target or f.getKey() = target or f.getValue() = target)) or
  exists(UCODE::ForInAltStatement f | not exists(f.getKind()) and
    (f.getVariable() = target or f.getKey() = target or f.getValue() = target))
}

private predicate cursorCompetitor(UCODE::Identifier id) {
  exists(UCODE::VariableDeclarator d | d.getName() = id) or
  exists(UCODE::FunctionDeclaration f | f.getName() = id) or
  exists(UCODE::FunctionExpression f | f.getName() = id) or
  exists(UCODE::FormalParameters ps | id = ps.getChild(_)) or
  exists(UCODE::RestElement rest, UCODE::FormalParameters ps |
    rest = ps.getChild(_) and id = rest.getChild()) or
  exists(UCODE::ArrowFunction f | f.getParameter() = id) or
  exists(UCODE::CatchClause c | c.getParameter() = id) or
  exists(UCODE::ForInStatement f | id = f.getVariable() or id = f.getKey() or id = f.getValue()) or
  exists(UCODE::ForInAltStatement f | id = f.getVariable() or id = f.getKey() or id = f.getValue()) or
  write(id)
}

/** A receiver identifier wrapped only in parentheses. */
private predicate parenthesizedBase(UCODE::Identifier id, UCODE::AstNode base) {
  base = id or exists(UCODE::ParenthesizedExpression p |
    p = base and parenthesizedBase(id, p.getChild())
  )
}

/** A raw read is proven to bind one distinct modeled local declaration. */
private predicate definitelyOtherRead(UCODE::Identifier id, UCODE::VariableDeclarator decl) {
  strictcount(VariableReadAccess r | toTreeSitter(r.getAstNode()) = id) = 1 and
  exists(VariableReadAccess r |
    toTreeSitter(r.getAstNode()) = id and toTreeSitter(r.getVariable().getAstNode()) != decl
  )
}

/** Association only: no runtime UCI target or effects are established. */
predicate sourceDeclaredUciCommit(
  UCODE::CallExpression call, UCODE::ImportStatement imp, UCODE::ImportSpecifier spec,
  UCODE::VariableDeclarator decl, UCODE::CallExpression init, UCODE::Identifier receiver,
  UCODE::String config
) {
  exists(UCODE::AstNode fn, UCODE::MemberExpression member, VariableReadAccess read |
    member = call.getFunction() and receiver = member.getObject() and
    member.getProperty().getValue() = "commit" and
    not exists(member.getOptionalChain()) and not exists(call.getOptionalChain()) and
    config = call.getArguments().getChild(0) and not exists(call.getArguments().getChild(1)) and
    config.getChild(0) instanceof UCODE::StringFragment and not exists(config.getChild(1)) and
    decl.getParent() instanceof UCODE::LexicalDeclaration and
    init = decl.getValue() and init.getFunction().(UCODE::Identifier).getValue() = "cursor" and
    not exists(init.getOptionalChain()) and not exists(init.getArguments().getChild(0)) and
    toTreeSitter(read.getAstNode()) = receiver and toTreeSitter(read.getVariable().getAstNode()) = decl and
    strictcount(VariableReadAccess candidate | toTreeSitter(candidate.getAstNode()) = receiver) = 1 and
    nearestFunction(decl, fn) and nearestFunction(call, fn) and before(decl, call) and
    imp.getParent() instanceof UCODE::Program and before(imp, fn) and
    not exists(UCODE::AstNode enclosing |
      functionNode(enclosing) and fn.getParent+() = enclosing and not before(imp, enclosing)
    ) and
    imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "uci" and
    not exists(imp.getSource().getChild(1)) and
    spec = imp.getClause().getNamed().getChild(_) and
    spec.getName().(UCODE::Identifier).getValue() = "cursor" and not exists(spec.getAlias()) and
    strictcount(UCODE::ImportStatement other, UCODE::Identifier id |
      id = importBinding(other) and id.getValue() = "cursor" and
      other.getLocation().getFile() = call.getLocation().getFile()
    ) = 1 and
    not exists(UCODE::Identifier id |
      id.getLocation().getFile() = call.getLocation().getFile() and
      id.getValue() = "cursor" and cursorCompetitor(id)
    ) and
    not exists(UCODE::VariableDeclarator other |
      other != decl and other.getName().getValue() = receiver.getValue() and
      other.getParent().getParent() = decl.getParent().getParent()
    ) and
    not exists(UCODE::Identifier other |
      other.getValue() = receiver.getValue() and other.getParent+() = fn and
      (exists(UCODE::FunctionDeclaration f | f.getName() = other) or
       exists(UCODE::FunctionExpression f | f.getName() = other))
    ) and
    not exists(UCODE::Identifier id |
      id.getValue() = receiver.getValue() and id.getLocation().getFile() = call.getLocation().getFile() and
      (id.getParent+() = fn or not exists(UCODE::AstNode f | functionNode(f) and id.getParent+() = f)) and
      (
        write(id) and
        (not exists(VariableWriteAccess w | toTreeSitter(w.getAstNode()) = id) or
         strictcount(VariableWriteAccess w | toTreeSitter(w.getAstNode()) = id) != 1 or
         exists(VariableWriteAccess w | toTreeSitter(w.getAstNode()) = id and
           toTreeSitter(w.getVariable().getAstNode()) = decl))
        or exists(UCODE::MemberExpression m | parenthesizedBase(id, m.getObject()) and write(m) and not definitelyOtherRead(id, decl))
        or exists(UCODE::SubscriptExpression m | parenthesizedBase(id, m.getObject()) and write(m) and not definitelyOtherRead(id, decl))
      )
    ) and
    not exists(ExtractionError error | error.getLocation().getFile() = call.getLocation().getFile())
  )
}
