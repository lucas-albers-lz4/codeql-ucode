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
final class ProgramScope extends CfgScopeImpl instanceof Program {
  override predicate scopeFirst(AstNode first) { first(Program.super.getStmt(0), first) }

  override predicate scopeLast(AstNode last, Completion c) { last(this, last, c) }

  Stmts getStmt(int index) { result = Program.super.getStmt(index) }
}
/**
 * A StatementBlock statement sequence
 */
final class StatementBlockScope extends CfgScopeImpl instanceof StatementBlock {
  override predicate scopeFirst(AstNode first) { first(StatementBlock.super.getStmt(0), first) }

  override predicate scopeLast(AstNode last, Completion c) { last(this, last, c) }

  Stmts getStmt(int index) { result = StatementBlock.super.getStmt(index) }
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