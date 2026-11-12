/**
 * Internal: Control flow graph construction for ucode.
 */

private import ucode
// CFG
import codeql.controlflow.Cfg
import Completion
private import Scope as Scope
private import codeql.ucode.controlflow.ControlFlowGraph as Cfg
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

// private import codeql.Locations
private module Implementation implements InputSig<Location> {
  private import ucode as ucode
  private import Completion as C

  class AstNode = ucode::AstNode;

  class Completion = C::Completion;

  predicate completionIsNormal = C::completionIsNormal/1;

  predicate completionIsSimple = C::completionIsSimple/1;

  predicate completionIsValidFor = C::completionIsValidFor/2;

  /** An AST node with an associated control-flow graph. */
  class CfgScope = Scope::CfgScope;

  class SuccessorType = Cfg::SuccessorType;

  CfgScope getCfgScope(AstNode e) {
    exists(AstNode p | p = e.getParent() |
      result = p
      or
      not p instanceof CfgScope and result = getCfgScope(p)
    )
  }

  /** Holds if `first` is first executed when entering `scope`. */
  predicate scopeFirst(CfgScope scope, AstNode first) { scope.scopeFirst(first) }

  /** Holds if `scope` is exited when `last` finishes with completion `c`. */
  predicate scopeLast(CfgScope scope, AstNode last, Completion c) { scope.scopeLast(last, c) }

  predicate successorTypeIsSimple(SuccessorType t) { t instanceof Cfg::NormalSuccessor }

  predicate successorTypeIsCondition(SuccessorType t) { t instanceof Cfg::BooleanSuccessor }

  SuccessorType getAMatchingSuccessorType(Completion c) { result = c.getAMatchingSuccessorType() }

  predicate isAbnormalExitType(SuccessorType t) { none() }
}

private module CfgImpl = Make<Location, Implementation>;

import CfgImpl

/**
 * A Program statement sequence
 */
class ProgramScopeTree extends StandardPreOrderTree, Scope::ProgramScope {
  override AstNode getChildNode(int i) { result = super.getStmt(i) }
}

/**
 * A StatementBlock statement sequence
 */
class StatementBlockScopeTree extends StandardPreOrderTree, Scope::StatementBlockScope {
  override AstNode getChildNode(int i) { result = super.getStmt(i) }
}

/** Nested blocks participate in their enclosing callable's CFG. */
class NestedStatementBlockTree extends StandardPreOrderTree, StatementBlock {
  NestedStatementBlockTree() { not this instanceof Scope::StatementBlockScope }

  override AstNode getChildNode(int i) { result = super.getStmt(i) }
}

/** An if executes its condition and then one of its branches. */
class IfStatementTree extends PreOrderTree, IfStatement {
  private UCODE::IfStatement raw() { this = TIfStatement(result) }

  private AstNode consequence() {
    toTreeSitter(result) = this.raw().getConsequence() and
    not result instanceof TStatement and
    not result instanceof TDeclaration
  }

  private AstNode alternative() {
    toTreeSitter(result) = this.raw().getAlternative().getChild() and
    not result instanceof TStatement and
    not result instanceof TDeclaration
  }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.consequence() or child = this.alternative()
  }

  override predicate last(AstNode last, Completion c) {
    last(this.consequence(), last, c)
    or
    last(this.alternative(), last, c)
    or
    not exists(this.alternative()) and last = this and completionIsSimple(c)
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    pred = this and
    completionIsSimple(c) and
    (first(this.consequence(), succ) or first(this.alternative(), succ))
  }
}

class CallDefinitionTree extends StandardPreOrderTree, Scope::CallDefinitionScope {
  override AstNode getChildNode(int i) { i = 0 and result = this.getStmt(i) }
}

/**
 * Most statements are leaves in this slice; if statements and nested blocks
 * have explicit control flow. Expressions are not evaluated independently.
 */
class StmtsTree extends LeafTree instanceof Stmts {
  StmtsTree() { not this instanceof StmtSequence and not this instanceof IfStatement }
}

/**
 * Expressions that are not already statements, sequences, or literals.
 */
class ExprTree extends LeafTree instanceof Expr {
  ExprTree() {
    not this instanceof Stmts and
    not this instanceof StmtSequence and
    not this instanceof Literals
  }
}

/**
 * A loop expression in a ucode program.
 */
abstract class LoopingExprTree extends PostOrderTree {
  override predicate propagatesAbnormal(AstNode child) { child = this.getLoopBody() }

  abstract StmtSequence getLoopBody();

  /**
   * Gets the node to execute when continuing the loop; either after
   * executing the last node in the body or after an explicit `continue`.
   */
  abstract AstNode getLoopContinue();

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    // Edge back to the start for final expression and continue expressions
    last(this.getLoopBody(), pred, c) and
    completionIsNormal(c) and
    first(this.getLoopContinue(), succ)
  }
}

/**
 * A literal value in a ucode program.
 */
class LiteralTree extends LeafTree instanceof Literals { }
