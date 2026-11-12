private import codeql.util.Boolean
private import codeql.util.Unit
private import codeql.ucode.ast.Expr
private import codeql.ucode.AST
private import codeql.ucode.CFG
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter
private import codeql.ucode.dataflow.Ssa
private import DataFlowPublic
private import DataFlowDispatch

/** Gets the callable in which this node occurs. */
DataFlowCallable nodeGetEnclosingCallable(Node n) { result = n.(NodeImpl).getEnclosingCallable() }

/** Holds if `p` is a `ParameterNode` of `c` with position `pos`. */
predicate isParameterNode(ParameterNodeImpl p, DataFlowCallable c, ParameterPosition pos) {
  p.isParameterOf(c, pos)
}

/** Holds if `arg` is an `ArgumentNode` of `c` with position `pos`. */
predicate isArgumentNode(ArgumentNode arg, DataFlowCall c, ArgumentPosition pos) {
  arg.argumentOf(c, pos)
}

abstract class NodeImpl extends Node {
  DataFlowCallable getEnclosingCallable() { result = TCfgScope(this.getCfgScope()) }

  /** Do not call: use `getEnclosingCallable()` instead. */
  abstract CfgScope getCfgScope();

  /** Do not call: use `getLocation()` instead. */
  abstract Location getLocationImpl();

  /** Do not call: use `toString()` instead. */
  abstract string toStringImpl();
}

private class ExprNodeImpl extends ExprNode, NodeImpl {
  override CfgScope getCfgScope() { result = this.getExprNode().getScope() }

  override Location getLocationImpl() { result = this.getExprNode().getLocation() }

  override string toStringImpl() { result = this.getExprNode().toString() }
}

private class SsaDefNodeImpl extends SsaDefinitionNode, NodeImpl {
  override CfgScope getCfgScope() { result = this.getCfgNode().getScope() }

  override Location getLocationImpl() { result = this.getDefinition().getLocation() }

  override string toStringImpl() {
    result = "ssa def " + this.getDefinition().getSourceVariable().getName()
  }
}

private class SsaReadNodeImpl extends SsaReadNode, NodeImpl {
  override CfgScope getCfgScope() { result = this.getRead().getScope() }

  override Location getLocationImpl() { result = this.getRead().getLocation() }

  override string toStringImpl() {
    result = "ssa read " + this.getDefinition().getSourceVariable().getName()
  }
}

/**
 * SSA value flow with per-definition identities.
 *
 * Wrapper CFG leaves are statements, so this does not treat a statement as
 * one value. A write flows to its own reads; identifier copies flow when the
 * assigned RHS (parens / comma-last / assignment-expression unwrapped) is
 * that identifier. Not call resolution (`viableSourceCallable` stays
 * `none()`) and not imported luci.sys `path_found`.
 */
module SsaFlow {
  /**
   * Innermost CFG node containing `inner`. Same rule as SSA: statement-level
   * leaves, so a nested function's CFG node wins over the enclosing statement.
   */
  private predicate astInCfg(CfgNode n, AstNode inner) {
    inner.getParent*() = n.getAstNode() and
    not exists(CfgNode closer |
      closer != n and
      inner.getParent*() = closer.getAstNode() and
      closer.getAstNode().getParent+() = n.getAstNode()
    )
  }

  /**
   * Value of `e` after stripping parentheses, taking the last comma operand,
   * and taking the RHS of a nested assignment expression (`a = b = x`).
   */
  private UCODE::AstNode copyValue(UCODE::AstNode e) {
    result = copyValue(e.(UCODE::ParenthesizedExpression).getChild())
    or
    exists(UCODE::SequenceExpression seq, int last |
      e = seq and
      last = max(int i | exists(seq.getChild(i))) and
      result = copyValue(seq.getChild(last))
    )
    or
    exists(UCODE::AssignmentExpression a |
      e = a and
      result = copyValue(a.getRight())
    )
    or
    not e instanceof UCODE::ParenthesizedExpression and
    not e instanceof UCODE::SequenceExpression and
    not e instanceof UCODE::AssignmentExpression and
    result = e
  }

  /** RHS expression stored by `dstDef` (declarator initializer or `=` RHS). */
  private UCODE::AstNode assignedRhs(Ssa::WriteDefinition dstDef) {
    exists(Variable v, UCODE::VariableDeclarator d |
      v = dstDef.getSourceVariable() and
      v.getAstNode() = TVariableDeclarator(d) and
      astInCfg(dstDef.getControlFlowNode(), v.getAstNode()) and
      result = d.getValue()
    )
    or
    exists(VariableWriteAccess wa, UCODE::Identifier ident, UCODE::AssignmentExpression a |
      wa.getVariable() = dstDef.getSourceVariable() and
      astInCfg(dstDef.getControlFlowNode(), wa.getAstNode()) and
      wa.getAstNode() = TIdentifier(ident) and
      a.getLeft() = ident and
      result = a.getRight()
    )
  }

  /** Write of `def` to a statement-level read of that same definition. */
  predicate ssaDefToRead(Node nodeFrom, Node nodeTo) {
    exists(Ssa::WriteDefinition def, CfgNode read |
      nodeFrom = TSsaDefNode(def) and
      read = def.getARead() and
      nodeTo = TSsaReadNode(def, read)
    )
  }

  /**
   * Identifier copy: the assigned value of `dstDef` is a read of `srcDef`.
   * Does not step through calls, field reads, or independent declarators.
   */
  predicate identifierCopy(Node nodeFrom, Node nodeTo) {
    exists(
      Ssa::WriteDefinition srcDef, Ssa::WriteDefinition dstDef, CfgNode read,
      VariableReadAccess ra, UCODE::Identifier ident
    |
      nodeFrom = TSsaReadNode(srcDef, read) and
      nodeTo = TSsaDefNode(dstDef) and
      read = dstDef.getControlFlowNode() and
      srcDef.getSourceVariable() != dstDef.getSourceVariable() and
      ra.getVariable() = srcDef.getSourceVariable() and
      astInCfg(read, ra.getAstNode()) and
      toTreeSitter(ra.getAstNode()) = ident and
      copyValue(assignedRhs(dstDef)) = ident
    )
  }

  predicate localFlowStep(Node nodeFrom, Node nodeTo) {
    ssaDefToRead(nodeFrom, nodeTo)
    or
    identifierCopy(nodeFrom, nodeTo)
  }
}

/** Provides predicates related to local data flow. */
module LocalFlow {
  pragma[nomagic]
  predicate localFlowStepCommon(Node nodeFrom, Node nodeTo) {
    none()
  }

  predicate localMustFlowStep(Node node1, Node node2) { none() }
}

/** An argument of a call (including qualifier arguments and block arguments). */
private class ArgumentExpr extends CfgNodes::ExprCfgNode {
  private CfgNodes::StmtNodes::CallCfgNode call;
  private ArgumentPosition arg;

  ArgumentExpr() { none() }

  /** Holds if this expression is the `i`th argument of `c`. */
  predicate isArgumentOf(CfgNodes::StmtNodes::CallCfgNode c, ArgumentPosition pos) {
    c = call and pos = arg
  }
}

/** Provides logic related to captured variables. */
module VariableCapture {
  // TODO
}

/** A collection of cached types and predicates to be evaluated in the same stage. */
cached
private module Cached {
  cached
  newtype TNode =
    TExprNode(CfgNodes::ExprCfgNode n) or
    // Per-definition SSA identities. Do not use statement CFG nodes: those
    // collapse unrelated values in one statement into one DataFlow node.
    TSsaDefNode(Ssa::WriteDefinition def) or
    TSsaReadNode(Ssa::WriteDefinition def, CfgNode read) { read = def.getARead() } or
    TExprPostUpdateNode(CfgNodes::ExprCfgNode n) {
      none() // TODO
    }

  cached
  Location getLocation(NodeImpl n) { result = n.getLocationImpl() }

  cached
  string toString(NodeImpl n) { result = n.toStringImpl() }

  /**
   * This is the local flow predicate that is used as a building block in global
   * data flow.
   */
  cached
  predicate simpleLocalFlowStep(Node nodeFrom, Node nodeTo, string model) {
    SsaFlow::localFlowStep(nodeFrom, nodeTo) and
    model = ""
  }

  /** This is the local flow predicate that is exposed. */
  cached
  predicate localFlowStepImpl(Node nodeFrom, Node nodeTo) {
    LocalFlow::localFlowStepCommon(nodeFrom, nodeTo)
    or
    SsaFlow::localFlowStep(nodeFrom, nodeTo)
  }

  cached
  newtype TContentSet = TSingletonContent(Content c)

  cached
  newtype TContent = TFieldContent(string name) { none() }

  cached
  newtype TContentApprox = TNonElementContentApprox(Content c) // TODO

  cached
  newtype TDataFlowType = TUnknownDataFlowType()
}

import Cached

/** Holds if `n` should be hidden from path explanations. */
predicate nodeIsHidden(Node n) { none() }

private module ParameterNodes {
  abstract class ParameterNodeImpl extends NodeImpl {
    abstract Expr getParameter();

    abstract predicate isParameterOf(DataFlowCallable c, ParameterPosition pos);

    final predicate isSourceParameterOf(CfgScope c, ParameterPosition pos) {
      exists(DataFlowCallable callable |
        this.isParameterOf(callable, pos) and
        c = callable.asCfgScope()
      )
    }
  }
  // TODO
}

import ParameterNodes

/** A data-flow node that represents a call argument. */
abstract class ArgumentNode extends Node {
  /** Holds if this argument occurs at the given position in the given call. */
  abstract predicate argumentOf(DataFlowCall call, ArgumentPosition pos);

  abstract predicate sourceArgumentOf(CfgNodes::StmtNodes::CallCfgNode call, ArgumentPosition pos);

  /** Gets the call in which this node is an argument. */
  final DataFlowCall getCall() { this.argumentOf(result, _) }
}

module ArgumentNodes {
  // TODO
}

import ArgumentNodes

/** A data-flow node that represents a value returned by a callable. */
abstract class ReturnNode extends Node {
  /** Gets the kind of this return node. */
  abstract ReturnKind getKind();
}

private module ReturnNodes {
  // TODO
}

import ReturnNodes

/** A data-flow node that represents the output of a call. */
abstract class OutNode extends Node {
  /** Gets the underlying call, where this node is a corresponding output of kind `kind`. */
  abstract DataFlowCall getCall(ReturnKind kind);
}

private module OutNodes {
  // TODO
}

import OutNodes

predicate jumpStep(Node pred, Node succ) {
  none() // TODO
}

/**
 * Holds if data can flow from `node1` to `node2` via an assignment to
 * content `c`.
 */
predicate storeStep(Node node1, ContentSet c, Node node2) {
  none() // TODO
}

/**
 * Holds if there is a read step of content `c` from `node1` to `node2`.
 */
predicate readStep(Node node1, ContentSet c, Node node2) {
  none() // TODO
}

/**
 * Holds if values stored inside content `c` are cleared at node `n`. For example,
 * any value stored inside `f` is cleared at the pre-update node associated with `x`
 * in `x.f = newValue`.
 */
predicate clearsContent(Node n, ContentSet c) {
  none() // TODO
}

/**
 * Holds if the value that is being tracked is expected to be stored inside content `c`
 * at node `n`.
 */
predicate expectsContent(Node n, ContentSet c) {
  none() // TODO
}

class DataFlowType extends TDataFlowType {
  string toString() { result = "" }
}

predicate typeStrongerThan(DataFlowType t1, DataFlowType t2) {
  t1 != TUnknownDataFlowType() and
  t2 = TUnknownDataFlowType()
}

predicate localMustFlowStep(Node node1, Node node2) { none() }

/** Gets the type of `n` used for type pruning. */
DataFlowType getNodeType(Node n) {
  exists(n) and
  result = TUnknownDataFlowType()
}

pragma[inline]
private predicate compatibleTypesNonSymRefl(DataFlowType t1, DataFlowType t2) {
  t1 != TUnknownDataFlowType() and
  t2 = TUnknownDataFlowType()
}

/**
 * Holds if `t1` and `t2` are compatible, that is, whether data can flow from
 * a node of type `t1` to a node of type `t2`.
 */
predicate compatibleTypes(DataFlowType t1, DataFlowType t2) {
  t1 = t2
  or
  compatibleTypesNonSymRefl(t1, t2)
  or
  compatibleTypesNonSymRefl(t2, t1)
}

abstract class PostUpdateNodeImpl extends Node {
  /** Gets the node before the state update. */
  abstract Node getPreUpdateNode();
}

private module PostUpdateNodes {
  // TODO
}

private import PostUpdateNodes

/** A node that performs a type cast. */
class CastNode extends Node {
  CastNode() { none() }
}

class DataFlowExpr = CfgNodes::ExprCfgNode;

/**
 * Holds if access paths with `c` at their head always should be tracked at high
 * precision. This disables adaptive access path precision for such access paths.
 */
predicate forceHighPrecision(Content c) { none() }

class NodeRegion instanceof Unit {
  string toString() { result = "NodeRegion" }

  predicate contains(Node n) { none() }

  /** Gets a best-effort total ordering. */
  int totalOrder() { none() }
}

/**
 * Holds if the nodes in `nr` are unreachable when the call context is `call`.
 */
predicate isUnreachableInCall(NodeRegion nr, DataFlowCall call) { none() }

newtype LambdaCallKind = TLambdaCallKind()

/** Holds if `creation` is an expression that creates a lambda of kind `kind` for `c`. */
predicate lambdaCreation(Node creation, LambdaCallKind kind, DataFlowCallable c) { none() }

/**
 * Holds if `call` is a from-source lambda call of kind `kind` where `receiver`
 * is the lambda expression.
 */
predicate lambdaSourceCall(CfgNodes::StmtNodes::CallCfgNode call, LambdaCallKind kind, Node receiver) {
  none()
}

/**
 * Holds if `call` is a (from-source or from-summary) lambda call of kind `kind`
 * where `receiver` is the lambda expression.
 */
predicate lambdaCall(DataFlowCall call, LambdaCallKind kind, Node receiver) { none() }

/** Extra data-flow steps needed for lambda flow analysis. */
predicate additionalLambdaFlowStep(Node nodeFrom, Node nodeTo, boolean preservesValue) { none() }

predicate knownSourceModel(Node source, string model) { none() }

predicate knownSinkModel(Node sink, string model) { none() }

class DataFlowSecondLevelScope = Unit;

/**
 * Holds if flow is allowed to pass from parameter `p` and back to itself as a
 * side-effect, resulting in a summary from `p` to itself.
 *
 * One example would be to allow flow like `p.foo = p.bar;`, which is disallowed
 * by default as a heuristic.
 */
predicate allowParameterReturnInSelf(ParameterNodeImpl p) {
  none() // TODO
}

/** An approximated `Content`. */
class ContentApprox extends TContentApprox {
  string toString() {
    exists(Content c |
      this = TNonElementContentApprox(c) and
      result = c.toString()
    )
  }
}

/** Gets an approximated value for content `c`. */
ContentApprox getContentApprox(Content c) { result = TNonElementContentApprox(c) }

/**
 * A unit class for adding additional jump steps.
 *
 * Extend this class to add additional jump steps.
 */
class AdditionalJumpStep extends Unit {
  /**
   * Holds if data can flow from `pred` to `succ` in a way that discards call contexts.
   */
  abstract predicate step(Node pred, Node succ);
}
