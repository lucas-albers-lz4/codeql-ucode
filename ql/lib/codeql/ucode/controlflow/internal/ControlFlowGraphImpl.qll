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

class StatementListTree extends StandardPreOrderTree, TStatementList {
  private UCODE::StatementList raw() { this = TStatementList(result) }

  override AstNode getChildNode(int i) { result = canonicalNode(this.raw().getChild(i)) }
}

/** An if executes its condition and then one of its branches. */
class IfStatementTree extends ControlFlowTree, IfStatement {
  private UCODE::IfStatement raw() { this = TIfStatement(result) }

  AstNode condition() { toTreeSitter(result) = this.raw().getCondition() }

  override predicate first(AstNode n) { first(this.condition(), n) }

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
    not exists(this.alternative()) and last(this.condition(), last, c)
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    last(this.condition(), pred, c) and
    completionIsNormal(c) and
    (first(this.consequence(), succ) or first(this.alternative(), succ))
  }
}

/** Alternate if/elif/else syntax with condition evaluation in source order. */
class IfAltStatementTree extends ControlFlowTree, TIfAltStatement {
  private UCODE::IfAltStatement raw() { this = TIfAltStatement(result) }

  private UCODE::ElifClause elifAt(int i) {
    result =
      rank[i + 1](UCODE::ElifClause clause, int j |
        clause = this.raw().getElifClause(j)
      |
        clause order by j
      )
  }

  AstNode conditionAt(int i) {
    i = 0 and result = canonicalNode(this.raw().getCondition())
    or
    i > 0 and result = canonicalNode(this.elifAt(i - 1).getCondition())
  }

  private AstNode bodyAt(int i) {
    i = 0 and result = canonicalNode(this.raw().getConsequence())
    or
    i > 0 and result = canonicalNode(this.elifAt(i - 1).getConsequence())
  }

  private AstNode alternative() { result = canonicalNode(this.raw().getAlternative().getChild()) }

  override predicate first(AstNode n) { first(this.conditionAt(0), n) }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.conditionAt(_) or child = this.bodyAt(_) or child = this.alternative()
  }

  override predicate last(AstNode n, Completion c) {
    last(this.bodyAt(_), n, c)
    or
    last(this.alternative(), n, c)
    or
    exists(int i | not exists(this.bodyAt(i)) and last(this.conditionAt(i), n, c))
    or
    exists(int i |
      not exists(this.conditionAt(i + 1)) and
      not exists(this.alternative()) and
      last(this.conditionAt(i), n, c)
    )
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    exists(int i |
      last(this.conditionAt(i), pred, c) and
      (
        first(this.bodyAt(i), succ)
        or
        first(this.conditionAt(i + 1), succ)
        or
        not exists(this.conditionAt(i + 1)) and first(this.alternative(), succ)
      )
    )
  }
}

/** Ordered control flow for while statements. */
class WhileStatementTree extends PreOrderTree {
  WhileStatementTree() { this instanceof TWhileStatement or this instanceof TWhileAltStatement }

  private UCODE::WhileStatement raw() { this = TWhileStatement(result) }

  private UCODE::WhileAltStatement alt() { this = TWhileAltStatement(result) }

  AstNode condition() {
    result = canonicalNode(this.raw().getCondition()) or
    result = canonicalNode(this.alt().getCondition())
  }

  private AstNode body() {
    result = canonicalNode(this.raw().getBody()) or result = canonicalNode(this.alt().getBody())
  }

  override predicate propagatesAbnormal(AstNode child) { none() }

  override predicate last(AstNode n, Completion c) {
    last(this.condition(), n, c)
    or
    exists(BreakCompletion b | last(this.body(), n, b) and completionIsSimple(c))
    or
    last(this.body(), n, c) and
    not c instanceof BreakCompletion and
    not c instanceof ContinueCompletion and
    not completionIsNormal(c)
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    pred = this and first(this.condition(), succ) and completionIsSimple(c)
    or
    last(this.condition(), pred, c) and first(this.body(), succ) and completionIsNormal(c)
    or
    last(this.body(), pred, c) and first(this.condition(), succ) and completionIsNormal(c)
    or
    not exists(this.body()) and
    last(this.condition(), pred, c) and
    first(this.condition(), succ) and
    completionIsNormal(c)
    or
    exists(ContinueCompletion k |
      last(this.body(), pred, k) and first(this.condition(), succ) and completionIsSimple(c)
    )
  }
}

/** CFG for the initializer, condition, body and increment of `for`. */
class ForStatementTree extends PreOrderTree {
  ForStatementTree() { this instanceof TForStatement or this instanceof TForAltStatement }

  private UCODE::ForStatement raw() { this = TForStatement(result) }

  private UCODE::ForAltStatement alt() { this = TForAltStatement(result) }

  AstNode condition() {
    result = canonicalNode(this.raw().getCondition()) or
    result = canonicalNode(this.alt().getCondition())
  }

  AstNode initializer() {
    result = canonicalNode(this.raw().getInitializer()) or
    result = canonicalNode(this.alt().getInitializer())
  }

  AstNode increment() {
    result = canonicalNode(this.raw().getIncrement()) or
    result = canonicalNode(this.alt().getIncrement())
  }

  private AstNode body() {
    result = canonicalNode(this.raw().getBody()) or result = canonicalNode(this.alt().getBody())
  }

  override predicate propagatesAbnormal(AstNode child) { none() }

  override predicate last(AstNode n, Completion c) {
    last(this.condition(), n, c) and not this.condition() instanceof TEmptyStatement
    or
    exists(BreakCompletion b | last(this.body(), n, b) and completionIsSimple(c))
    or
    last(this.body(), n, c) and
    not c instanceof BreakCompletion and
    not c instanceof ContinueCompletion and
    not completionIsNormal(c)
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      pred = this and first(this.initializer(), succ)
      or
      pred = this and not exists(this.initializer()) and first(this.condition(), succ)
      or
      last(this.initializer(), pred, c) and first(this.condition(), succ)
      or
      last(this.condition(), pred, c) and first(this.body(), succ)
      or
      last(this.condition(), pred, c) and
      not exists(this.body()) and
      (
        first(this.increment(), succ)
        or
        not exists(this.increment()) and first(this.condition(), succ)
      )
      or
      last(this.body(), pred, c) and first(this.increment(), succ)
      or
      last(this.body(), pred, c) and not exists(this.increment()) and first(this.condition(), succ)
      or
      last(this.increment(), pred, c) and first(this.condition(), succ)
      or
      exists(ContinueCompletion k |
        last(this.body(), pred, k) and
        (
          first(this.increment(), succ)
          or
          not exists(this.increment()) and first(this.condition(), succ)
        )
      )
    )
  }
}

/** The bindings are written only after an iterator produces an item. */
class ForInBindingTree extends LeafTree, TStatement {
  ForInBindingTree() {
    exists(UCODE::ForInStatement f | this = TStatement(f)) or
    exists(UCODE::ForInAltStatement f | this = TStatement(f))
  }
}

/** Evaluate the iterable once, then choose zero or more body iterations. */
class ForInStatementTree extends PostOrderTree {
  ForInStatementTree() { this instanceof TForInStatement or this instanceof TForInAltStatement }

  private UCODE::ForInStatement raw() { this = TForInStatement(result) }

  private UCODE::ForInAltStatement alt() { this = TForInAltStatement(result) }

  AstNode iterable() {
    result = canonicalNode(this.raw().getObject()) or result = canonicalNode(this.alt().getObject())
  }

  private AstNode body() {
    result = canonicalNode(this.raw().getBody()) or result = canonicalNode(this.alt().getBody())
  }

  private AstNode binding() { result = TStatement(this.raw()) or result = TStatement(this.alt()) }

  override predicate first(AstNode n) { first(this.iterable(), n) }

  override predicate propagatesAbnormal(AstNode child) { child = this.iterable() }

  override predicate last(AstNode n, Completion c) {
    n = this and completionIsSimple(c)
    or
    exists(BreakCompletion b | last(this.body(), n, b) and completionIsSimple(c))
    or
    last(this.body(), n, c) and
    not c instanceof BreakCompletion and
    not c instanceof ContinueCompletion and
    not completionIsNormal(c)
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      last(this.iterable(), pred, c) and succ = this
      or
      pred = this and first(this.binding(), succ)
      or
      last(this.binding(), pred, c) and first(this.body(), succ)
      or
      last(this.binding(), pred, c) and not exists(this.body()) and succ = this
      or
      last(this.body(), pred, c) and succ = this
      or
      exists(ContinueCompletion k | last(this.body(), pred, k) and succ = this)
    )
  }
}

/** A case body executes its statements in order, then may fall through. */
class SwitchCaseTree extends StandardPreOrderTree {
  SwitchCaseTree() { this instanceof TSwitchCase or this instanceof TSwitchDefault }

  override AstNode getChildNode(int i) {
    exists(UCODE::SwitchCase c | this = TSwitchCase(c) and result = canonicalNode(c.getBody(i)))
    or
    exists(UCODE::SwitchDefault d |
      this = TSwitchDefault(d) and result = canonicalNode(d.getBody(i))
    )
  }
}

/** Evaluate case tests in order, enter the matching body, and preserve fallthrough. */
class SwitchStatementTree extends PreOrderTree, TSwitchStatement {
  private UCODE::SwitchStatement raw() { this = TSwitchStatement(result) }

  AstNode selector() { result = canonicalNode(this.raw().getValue()) }

  private AstNode caseAt(int i) {
    result =
      rank[i + 1](AstNode node, int j |
        node = canonicalNode(this.raw().getBody().getChild(j))
      |
        node order by j
      )
  }

  private AstNode testCaseAt(int i) {
    result =
      rank[i + 1](AstNode node, int j |
        node = canonicalNode(this.raw().getBody().getChild(j)) and node instanceof TSwitchCase
      |
        node order by j
      )
  }

  private AstNode test(AstNode caseNode) {
    exists(UCODE::SwitchCase c | caseNode = TSwitchCase(c) and result = canonicalNode(c.getValue()))
  }

  private AstNode defaultCase() { result = this.caseAt(_) and result instanceof TSwitchDefault }

  AstNode caseTest() { result = this.test(this.testCaseAt(_)) }

  override predicate propagatesAbnormal(AstNode child) { none() }

  override predicate last(AstNode n, Completion c) {
    exists(int i | not exists(this.caseAt(i + 1)) and last(this.caseAt(i), n, c))
    or
    exists(int i |
      not exists(this.defaultCase()) and
      not exists(this.testCaseAt(i + 1)) and
      last(this.test(this.testCaseAt(i)), n, c)
    )
    or
    not exists(this.caseAt(_)) and last(this.selector(), n, c)
    or
    exists(BreakCompletion b | last(this.caseAt(_), n, b) and completionIsSimple(c))
    or
    last(this.caseAt(_), n, c) and not c instanceof BreakCompletion and not completionIsNormal(c)
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      pred = this and first(this.selector(), succ)
      or
      last(this.selector(), pred, c) and first(this.test(this.testCaseAt(0)), succ)
      or
      last(this.selector(), pred, c) and
      not exists(this.testCaseAt(_)) and
      first(this.defaultCase(), succ)
      or
      exists(int i |
        last(this.test(this.testCaseAt(i)), pred, c) and
        (
          first(this.testCaseAt(i), succ)
          or
          first(this.test(this.testCaseAt(i + 1)), succ)
          or
          not exists(this.testCaseAt(i + 1)) and first(this.defaultCase(), succ)
        )
      )
      or
      exists(int i | last(this.caseAt(i), pred, c) and first(this.caseAt(i + 1), succ))
    )
  }
}

/** Enter the catch scope before executing its body. */
class CatchClauseTree extends StandardPreOrderTree, TCatchClause {
  private UCODE::CatchClause raw() { this = TCatchClause(result) }

  override AstNode getChildNode(int i) { i = 0 and result = canonicalNode(this.raw().getBody()) }
}

/** Evaluate the return value before the callable exits. */
class ReturnStatementTree extends StandardPostOrderTree, TReturnStatement {
  private UCODE::ReturnStatement raw() { this = TReturnStatement(result) }

  AstNode value() { result = canonicalNode(this.raw().getChild()) }

  override AstNode getChildNode(int i) { i = 0 and result = this.value() }
}

/** Exported declarations and default expressions evaluate their wrapped values. */
class ExportStatementTree extends StandardPostOrderTree, TExportStatement {
  private UCODE::ExportStatement raw() { this = TExportStatement(result) }

  AstNode value() { result = canonicalNode(this.raw().getValue()) }

  override AstNode getChildNode(int i) {
    i = 0 and
    (result = canonicalNode(this.raw().getDeclaration()) or result = this.value())
  }
}

/** Operations that may transfer control to a surrounding catch. */
private predicate mayThrow(AstNode n) {
  n instanceof TCallExpression
  or
  n instanceof TMemberExpression
  or
  n instanceof TSubscriptExpression
  or
  n instanceof TBinaryExpression
  or
  n instanceof TUnaryExpression
  or
  n instanceof TAugmentedAssignmentExpression
  or
  n instanceof TUpdateExpression
  or
  n instanceof TDeleteExpression
  or
  n instanceof TForInStatement
  or
  n instanceof TForInAltStatement
  or
  n instanceof ForInBindingTree
  or
  n instanceof LogicalAssignmentWriteTree
  or
  exists(UCODE::AssignmentExpression a |
    n = TAssignmentExpression(a) and not a.getLeft() instanceof UCODE::Identifier
  )
}

/** A throwing operation transfers to the handler before the operation writes a value. */
class TryStatementTree extends PreOrderTree, TTryStatement {
  private UCODE::TryStatement raw() { this = TTryStatement(result) }

  private AstNode body() { result = canonicalNode(this.raw().getBody()) }

  private AstNode handler() { result = canonicalNode(this.raw().getHandler()) }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.body() or child = this.handler()
  }

  override predicate last(AstNode n, Completion c) {
    last(this.body(), n, c) or last(this.handler(), n, c)
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    pred = this and first(this.body(), succ) and completionIsSimple(c)
    or
    exists(AstNode operation |
      operation.getParent*() = this.body() and
      mayThrow(operation) and
      not exists(AstNode fn |
        (
          fn instanceof TFunctionExpression or
          fn instanceof TArrowFunction or
          fn instanceof TFunctionDeclaration
        ) and
        operation.getParent+() = fn and
        fn.getParent+() = this.body()
      ) and
      CfgImpl::succ(pred, operation, c) and
      completionIsNormal(c) and
      first(this.handler(), succ)
    )
  }
}

class CallDefinitionTree extends StandardPreOrderTree, Scope::CallDefinitionScope {
  override AstNode getChildNode(int i) { i = 0 and result = this.getStmt(i) }
}

/**
 * Statements without special control-flow behavior remain leaves.
 */
class StmtsTree extends LeafTree instanceof Stmts {
  StmtsTree() {
    not this instanceof StmtSequence and
    not this instanceof IfStatement and
    not this instanceof WhileStatementTree and
    not this instanceof ForStatementTree and
    not this instanceof ForInStatementTree and
    not this instanceof TSwitchStatement and
    not this instanceof TIfAltStatement and
    not this instanceof TStatementList and
    not this instanceof TTryStatement and
    not this instanceof TReturnStatement and
    not this instanceof TExportStatement and
    not this instanceof TLexicalDeclaration and
    not this instanceof TExpressionStatement and
    not this instanceof EvaluationTree
  }
}

private predicate isChoiceExpression(AstNode n) {
  n instanceof TTernaryExpression
  or
  exists(UCODE::BinaryExpression b |
    n = TBinaryExpression(b) and b.getOperator() in ["&&", "||", "??"]
  )
  or
  exists(UCODE::AugmentedAssignmentExpression a |
    n = TAugmentedAssignmentExpression(a) and a.getOperator() in ["&&=", "||=", "??="]
  )
  or
  exists(UCODE::CallExpression c | n = TCallExpression(c) and optionalCall(c))
  or
  exists(UCODE::SubscriptExpression s | n = TSubscriptExpression(s) and optionalSubscript(s))
}

/** A chain remains optional through contiguous member, subscript and call operations. */
private predicate hasOptionalChain(UCODE::AstNode n) {
  exists(UCODE::MemberExpression m |
    n = m and
    (exists(m.getOptionalChain()) or hasOptionalChain(m.getObject()))
  )
  or
  exists(UCODE::SubscriptExpression s |
    n = s and
    (exists(s.getOptionalChain()) or hasOptionalChain(s.getObject()))
  )
  or
  exists(UCODE::CallExpression c |
    n = c and
    (exists(c.getOptionalChain()) or hasOptionalChain(c.getFunction()))
  )
}

private predicate optionalCall(UCODE::CallExpression c) {
  exists(c.getOptionalChain()) or hasOptionalChain(c.getFunction())
}

private predicate optionalSubscript(UCODE::SubscriptExpression s) {
  exists(s.getOptionalChain()) or hasOptionalChain(s.getObject())
}

private AstNode canonicalNode(UCODE::AstNode raw) {
  toTreeSitter(result) = raw and
  not result instanceof TExpression and
  not result instanceof TPrimaryExpression and
  not result instanceof TStatement and
  not result instanceof TDeclaration
}

/** Choice expressions evaluate only one of their two arms. */
class TernaryTree extends PostOrderTree, TTernaryExpression {
  private UCODE::TernaryExpression raw() { this = TTernaryExpression(result) }

  private AstNode condition() { result = canonicalNode(this.raw().getCondition()) }

  private AstNode arm() {
    result = canonicalNode(this.raw().getConsequence()) or
    result = canonicalNode(this.raw().getAlternative())
  }

  override predicate first(AstNode n) { first(this.condition(), n) }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.condition() or child = this.arm()
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      last(this.condition(), pred, c) and first(this.arm(), succ)
      or
      last(this.arm(), pred, c) and succ = this
    )
  }
}

/** The right side of a logical expression may be skipped. */
class ShortCircuitTree extends PostOrderTree, TBinaryExpression {
  private UCODE::BinaryExpression raw() { this = TBinaryExpression(result) }

  ShortCircuitTree() {
    exists(UCODE::BinaryExpression b |
      this = TBinaryExpression(b) and b.getOperator() in ["&&", "||", "??"]
    )
  }

  private AstNode left() { result = canonicalNode(this.raw().getLeft()) }

  private AstNode right() { result = canonicalNode(this.raw().getRight()) }

  override predicate first(AstNode n) { first(this.left(), n) }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.left() or child = this.right()
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      last(this.left(), pred, c) and
      (succ = this or first(this.right(), succ))
      or
      last(this.right(), pred, c) and succ = this
    )
  }
}

/** Optional calls evaluate their arguments only when the chain continues. */
class OptionalCallTree extends PostOrderTree, TCallExpression {
  OptionalCallTree() {
    exists(UCODE::CallExpression c | this = TCallExpression(c) and optionalCall(c))
  }

  private UCODE::CallExpression raw() { this = TCallExpression(result) }

  private AstNode callee() { result = canonicalNode(this.raw().getFunction()) }

  private AstNode arguments() { result = canonicalNode(this.raw().getArguments()) }

  override predicate first(AstNode n) { first(this.callee(), n) }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.callee() or child = this.arguments()
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      last(this.callee(), pred, c) and
      (succ = this or first(this.arguments(), succ))
      or
      last(this.arguments(), pred, c) and succ = this
    )
  }
}

/** Optional subscripts evaluate their index only when the chain continues. */
class OptionalSubscriptTree extends PostOrderTree, TSubscriptExpression {
  OptionalSubscriptTree() {
    exists(UCODE::SubscriptExpression s | this = TSubscriptExpression(s) and optionalSubscript(s))
  }

  private UCODE::SubscriptExpression raw() { this = TSubscriptExpression(result) }

  private AstNode object() { result = canonicalNode(this.raw().getObject()) }

  private AstNode index() { result = canonicalNode(this.raw().getIndex()) }

  override predicate first(AstNode n) { first(this.object(), n) }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.object() or child = this.index()
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      last(this.object(), pred, c) and
      (succ = this or first(this.index(), succ))
      or
      last(this.index(), pred, c) and succ = this
    )
  }
}

/** Distinct write and result nodes keep a skipped logical assignment from killing the old value. */
class LogicalAssignmentWriteTree extends LeafTree, TExpression {
  LogicalAssignmentWriteTree() {
    exists(UCODE::AugmentedAssignmentExpression a |
      this = TExpression(a) and a.getOperator() in ["&&=", "||=", "??="]
    )
  }
}

class LogicalAssignmentTree extends PostOrderTree, TAugmentedAssignmentExpression {
  private UCODE::AugmentedAssignmentExpression raw() {
    this = TAugmentedAssignmentExpression(result)
  }

  LogicalAssignmentTree() {
    exists(UCODE::AugmentedAssignmentExpression a |
      this = TAugmentedAssignmentExpression(a) and a.getOperator() in ["&&=", "||=", "??="]
    )
  }

  private AstNode left() { result = canonicalNode(this.raw().getLeft()) }

  private AstNode right() { result = canonicalNode(this.raw().getRight()) }

  private AstNode write() { result = TExpression(this.raw()) }

  override predicate first(AstNode n) { first(this.left(), n) }

  override predicate propagatesAbnormal(AstNode child) {
    child = this.left() or child = this.right()
  }

  override predicate succ(AstNode pred, AstNode succ, Completion c) {
    completionIsNormal(c) and
    (
      last(this.left(), pred, c) and
      (succ = this or first(this.right(), succ))
      or
      last(this.right(), pred, c) and first(this.write(), succ)
      or
      last(this.write(), pred, c) and succ = this
    )
  }
}

/**
 * Expressions that are not already statements, sequences, or literals.
 */
class ExprTree extends LeafTree instanceof Expr {
  ExprTree() {
    not this instanceof Stmts and
    not this instanceof StmtSequence and
    not this instanceof Literals and
    not isChoiceExpression(this) and
    not this instanceof SwitchCaseTree and
    not exists(EvaluationTree e | this = e)
  }
}

/** Ordered evaluation of ordinary expressions and lexical declarations. */
class EvaluationTree extends StandardPostOrderTree {
  EvaluationTree() {
    not this instanceof TExpression and
    not this instanceof TPrimaryExpression and
    not isChoiceExpression(this) and
    (
      this instanceof TLexicalDeclaration
      or
      this instanceof TExpressionStatement
      or
      exists(AstNode root |
        (
          root instanceof TLexicalDeclaration or
          root instanceof TExpressionStatement or
          root = any(IfStatementTree i).condition() or
          root = any(IfAltStatementTree i).conditionAt(_) or
          root = any(WhileStatementTree w).condition() or
          root = any(ForStatementTree f).condition() or
          root = any(ForStatementTree f).initializer() or
          root = any(ForStatementTree f).increment() or
          root = any(ForInStatementTree f).iterable() or
          root = any(SwitchStatementTree s).selector() or
          root = any(SwitchStatementTree s).caseTest() or
          root = any(ReturnStatementTree r).value() or
          root = any(ExportStatementTree e).value()
        ) and
        this.getParent*() = root and
        not this instanceof TStatement and
        not this instanceof TDeclaration and
        not exists(AstNode f |
          (
            f instanceof TFunctionExpression or
            f instanceof TArrowFunction or
            f instanceof TFunctionDeclaration
          ) and
          this.getParent+() = f and
          f.getParent*() = root
        )
      )
    )
  }

  override AstNode getChildNode(int i) {
    result = this.getAChild() and
    not result instanceof TExpression and
    not result instanceof TPrimaryExpression and
    toTreeSitter(result).getParentIndex() = i and
    not this instanceof TFunctionExpression and
    not this instanceof TArrowFunction and
    not exists(UCODE::VariableDeclarator d |
      this = TVariableDeclarator(d) and toTreeSitter(result) = d.getName()
    ) and
    not exists(UCODE::AssignmentExpression a, UCODE::Identifier id |
      this = TAssignmentExpression(a) and a.getLeft() = id and toTreeSitter(result) = id
    )
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
class LiteralTree extends LeafTree instanceof Literals {
  LiteralTree() { not this instanceof EvaluationTree }
}
