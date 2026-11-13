private import ucode
private import codeql.ucode.AST
private import Completion
private import ControlFlowGraphImpl
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

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

/** Identifier at `FormalParameters` child `i`, including a rest binding. */
private UCODE::Identifier formalIdentAt(UCODE::FormalParameters ps, int i) {
  result = ps.getChild(i)
  or
  result = ps.getChild(i).(UCODE::RestElement).getChild()
}

/**
 * A StatementBlock statement sequence
 */
final class StatementBlockScope extends CfgScopeImpl instanceof StatementBlock {
  StatementBlockScope() {
    exists(UCODE::FunctionExpression f | toTreeSitter(this) = f.getBody()) or
    exists(UCODE::FunctionDeclaration f | toTreeSitter(this) = f.getBody()) or
    exists(UCODE::ArrowFunction f | toTreeSitter(this) = f.getBody())
  }

  /**
   * Named formal of the function whose body is this scope, in parameter
   * order. Formals are not AST children of the block; they still execute
   * first in this CFG.
   */
  AstNode getFormal(int i) {
    exists(UCODE::FunctionExpression f |
      toTreeSitter(this) = f.getBody() and
      result = TIdentifier(formalIdentAt(f.getParameters(), i))
    )
    or
    exists(UCODE::FunctionDeclaration f |
      toTreeSitter(this) = f.getBody() and
      result = TIdentifier(formalIdentAt(f.getParameters(), i))
    )
    or
    exists(UCODE::ArrowFunction f |
      toTreeSitter(this) = f.getBody() and
      (
        exists(UCODE::FormalParameters ps |
          ps = f.getParameters() and result = TIdentifier(formalIdentAt(ps, i))
        )
        or
        not exists(f.getParameters()) and
        i = 0 and
        result = TIdentifier(f.getParameter())
      )
    )
  }

  int getFormalCount() { result = count(int i | exists(this.getFormal(i))) }

  override predicate scopeFirst(AstNode first) {
    first(this.getFormal(0), first)
    or
    not exists(this.getFormal(_)) and first(StatementBlock.super.getStmt(0), first)
  }

  override predicate scopeLast(AstNode last, Completion c) { last(this, last, c) }

  Stmts getStmt(int index) { result = StatementBlock.super.getStmt(index) }
}

/**
 * A Call Definition Scope
 */
final class CallDefinitionScope extends CfgScopeImpl instanceof CallDefinition {
  override predicate scopeFirst(AstNode first) { first(CallDefinition.super.getStmt(0), first) }

  override predicate scopeLast(AstNode last, Completion c) { last(this, last, c) }

  AstNode getStmt(int index) { result = CallDefinition.super.getStmt(index) }
}
