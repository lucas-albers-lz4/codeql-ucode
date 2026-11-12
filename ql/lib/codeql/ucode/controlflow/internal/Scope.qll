private import ucode
private import codeql.ucode.AST
private import Completion
private import ControlFlowGraphImpl

/**
 * A scope in the control flow graph.
 */
abstract private class CfgScopeImpl extends AstNode {
  /** Holds if `first` is executed first when entering scope. */
  abstract predicate scopeFirst(AstNode first);

  /** Holds if scope is exited when `last` finishes with completion `c`. */
  abstract predicate scopeLast(AstNode last, Completion c);
}

final class CfgScope = CfgScopeImpl;
/**
 * A Program statement sequence
 */
final class ProgramScope extends CfgScopeImpl, Program {
  override predicate scopeFirst(AstNode first) { first(this.getStmt(0), first) }

  override predicate scopeLast(AstNode last, Completion c) { last(this, last, c) }
}
/**
 * A StatementBlock statement sequence
 */
final class StatementBlockScope extends CfgScopeImpl, StatementBlock {
  override predicate scopeFirst(AstNode first) { first(this.getStmt(0), first) }

  override predicate scopeLast(AstNode last, Completion c) { last(this, last, c) }
}

/**
 * A Call Definition Scope
 */
final class CallDefinitionScope extends CfgScopeImpl instanceof CallDefinition {
  override predicate scopeFirst(AstNode first) { first(CallDefinition.super.getStmt(0), first) }

  override predicate scopeLast(AstNode last, Completion c) { last(this, last, c) }

  AstNode getStmt(int index) {
    result = CallDefinition.super.getStmt(index)
  }
}