/** Conservative source-declared fs import attribution shared by Models and dataflow. */
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.Diagnostics

/** A local identifier introduced by any import clause in `imp`. */
private UCODE::Identifier fsImportBinding(UCODE::ImportStatement imp) {
  exists(UCODE::ImportSpecifier spec |
    spec = imp.getClause().getNamed().getChild(_) and
    (result = spec.getAlias() or not exists(spec.getAlias()) and result = spec.getName())
  )
  or result = imp.getClause().getDefault()
  or result = imp.getClause().getNamespace().getChild()
}

/** Competing binding or write, checked across the entire file. */
private predicate fsCompetingBindingOrWrite(UCODE::Identifier id) {
  exists(UCODE::VariableDeclarator d | d.getName() = id)
  or exists(UCODE::FunctionDeclaration f | f.getName() = id)
  or exists(UCODE::FunctionExpression f | f.getName() = id)
  or exists(UCODE::FormalParameters ps | id = ps.getChild(_))
  or exists(UCODE::RestElement rest, UCODE::FormalParameters ps |
    rest = ps.getChild(_) and id = rest.getChild()
  )
  or exists(UCODE::ArrowFunction f | f.getParameter() = id)
  or exists(UCODE::CatchClause c | c.getParameter() = id)
  or exists(UCODE::ForInStatement f | id = f.getVariable() or id = f.getKey() or id = f.getValue())
  or exists(UCODE::ForInAltStatement f | id = f.getVariable() or id = f.getKey() or id = f.getValue())
  or exists(UCODE::AssignmentExpression a | a.getLeft() = id)
  or exists(UCODE::AugmentedAssignmentExpression a | a.getLeft() = id)
  or exists(UCODE::UpdateExpression u | u.getArgument() = id)
}

/**
 * Direct unaliased named import from plain `fs`, before a direct call.
 * This is a deliberately conservative syntactic subset, not a runtime resolver.
 */
pragma[inline]
predicate sourceDeclaredFsCall(UCODE::CallExpression raw, string name) {
  name = ["popen", "basename", "access", "open", "readfile", "readlink"] and
  raw.getFunction() instanceof UCODE::Identifier and
  raw.getFunction().(UCODE::Identifier).getValue() = name and
  not exists(raw.getOptionalChain()) and
  exists(UCODE::ImportStatement imp, UCODE::ImportSpecifier spec |
    imp.getLocation().getFile() = raw.getLocation().getFile() and
    imp.getParent() instanceof UCODE::Program and
    (imp.getLocation().getEndLine() < raw.getLocation().getStartLine() or
      imp.getLocation().getEndLine() = raw.getLocation().getStartLine() and
      imp.getLocation().getEndColumn() < raw.getLocation().getStartColumn()) and
    spec = imp.getClause().getNamed().getChild(_) and
    spec.getName().(UCODE::Identifier).getValue() = name and
    not exists(spec.getAlias()) and
    imp.getSource().getChild(0).(UCODE::StringFragment).getValue() = "fs" and
    not exists(imp.getSource().getChild(1)) and
    strictcount(UCODE::ImportStatement other, UCODE::Identifier id |
      id = fsImportBinding(other) and
      other.getLocation().getFile() = raw.getLocation().getFile() and id.getValue() = name
    ) = 1 and
    not exists(UCODE::Identifier id |
      id.getLocation().getFile() = raw.getLocation().getFile() and
      id.getValue() = name and fsCompetingBindingOrWrite(id)
    ) and
    not exists(ExtractionError error | error.getLocation().getFile() = raw.getLocation().getFile())
  )
}
