private import ucode
private import DataFlowDispatch
private import DataFlowPrivate
private import codeql.ucode.controlflow.ControlFlowGraph
private import codeql.ucode.controlflow.CfgNodes as CfgNodes
private import codeql.ucode.dataflow.Ssa

/**
 * An element, viewed as a node in a data flow graph. Either an expression
 * (`ExprNode`), an SSA definition or read (`SsaDefinitionNode` /
 * `SsaReadNode`), a returned value (`ReturnValueNode`), or an entry parameter
 * (`ParameterNode`).
 *
 * SSA nodes retain the identity of individual definitions and reads.
 */
class Node extends TNode {
  /** Gets the expression corresponding to this node, if any. */
  CfgNodes::ExprCfgNode asExpr() { result = this.(ExprNode).getExprNode() }

  /**
   * Gets the CFG node for this SSA def or read, if any.
   *
   * This is a location, not a value identity. Public `localFlowStep` uses
   * `SsaDefinitionNode` / `SsaReadNode`.
   */
  CfgNode asCfgNode() {
    result = this.(SsaDefinitionNode).getCfgNode()
    or
    result = this.(SsaReadNode).getRead()
  }

  /** Gets the Expr corresponding to this node, if any. */
  Expr asParameter() { result = this.(ParameterNode).getParameter() }

  /** Gets a textual representation of this node. */
  final string toString() { result = toString(this) }

  /** Gets the location of this node. */
  final Location getLocation() { result = getLocation(this) }

  /**
   * Gets a data flow node from which data may flow to this node in one local step.
   */
  Node getAPredecessor() { localFlowStep(result, this) }

  /**
   * Gets a data flow node to which data may flow from this node in one local step.
   */
  Node getASuccessor() { localFlowStep(this, result) }
}

/**
 * An expression, viewed as a node in a data flow graph.
 *
 * Note that because of control-flow splitting, one `Expr` may correspond
 * to multiple `ExprNode`s, just like it may correspond to multiple
 * `ControlFlow::Node`s.
 */
class ExprNode extends Node, TExprNode {
  private CfgNodes::ExprCfgNode n;

  ExprNode() { this = TExprNode(n) }

  /** Gets the expression corresponding to this node. */
  CfgNodes::ExprCfgNode getExprNode() { result = n }
}

/**
 * An SSA write, viewed as a data-flow node.
 *
 * Distinct from other writes in the same statement. Public `localFlowStep`
 * from this node reaches this definition's reads, not every value in the
 * enclosing CFG statement.
 */
class SsaDefinitionNode extends Node, TSsaDefNode {
  private Ssa::WriteDefinition def;

  SsaDefinitionNode() { this = TSsaDefNode(def) }

  /** Gets the SSA write. */
  Ssa::WriteDefinition getDefinition() { result = def }

  /** Gets the CFG node of this write. */
  CfgNode getCfgNode() { result = def.getControlFlowNode() }
}

/**
 * A read of an SSA write, viewed as a data-flow node.
 *
 * Keyed by definition and read CFG node so a read of `x` is not a write of
 * `y` even when both occur in the same statement.
 */
class SsaReadNode extends Node, TSsaReadNode {
  private Ssa::WriteDefinition def;
  private CfgNode read;

  SsaReadNode() { this = TSsaReadNode(def, read) }

  /** Gets the SSA write being read. */
  Ssa::WriteDefinition getDefinition() { result = def }

  /** Gets the CFG node of this read. */
  CfgNode getRead() { result = read }
}

/** The value returned by a return statement in a callable. */
class ReturnValueNode extends Node, TReturnNode {
  private CfgNodes::AstCfgNode n;

  ReturnValueNode() { this = TReturnNode(n) }

  /** Gets the return statement's CFG node. */
  CfgNodes::AstCfgNode getCfgNode() { result = n }
}

/**
 * The value of a Expr at function entry, viewed as a node in a data
 * flow graph.
 */
class ParameterNode extends Node {
  ParameterNode() { exists(getParameterPosition(this, _)) }

  /** Gets the Expr corresponding to this node, if any. */
  final Expr getParameter() { result = getParameter(this) }
}

/**
 * A node associated with an object after an operation that might have
 * changed its state.
 *
 * This can be either the argument to a callable after the callable returns
 * (which might have mutated the argument), or the qualifier of a field after
 * an update to the field.
 *
 * Nodes corresponding to AST elements, for example `ExprNode`, usually refer
 * to the value before the update.
 */
class PostUpdateNode extends Node {
  private Node pre;

  PostUpdateNode() { pre = getPreUpdateNode(this) }

  /** Gets the node before the state update. */
  Node getPreUpdateNode() { result = pre }
}

cached
private module Cached {
  cached
  CfgScope getCfgScope(NodeImpl node) { result = node.getCfgScope() }

  cached
  Expr getParameter(ParameterNodeImpl param) { result = param.getParameter() }

  cached
  ParameterPosition getParameterPosition(ParameterNodeImpl param, DataFlowCallable c) {
    param.isParameterOf(c, result)
  }

  cached
  Node getPreUpdateNode(PostUpdateNodeImpl node) { result = node.getPreUpdateNode() }

  cached
  predicate forceCachingInSameStage() { any() }
}

private import Cached

/** Gets a node corresponding to expression `e`. */
ExprNode exprNode(CfgNodes::ExprCfgNode e) { result.getExprNode() = e }

/**
 * Gets the node corresponding to the value of Expr `p` at function entry.
 */
ParameterNode parameterNode(Expr p) { result.getParameter() = p }

/**
 * Holds if a value flows from `nodeFrom` to `nodeTo` in exactly one local
 * (intra-procedural) value-preserving step. Value-transforming operations,
 * such as arithmetic and `+=`, have no local flow edge; taint propagation
 * through those operations is not modeled here.
 */
predicate localFlowStep = localFlowStepImpl/2;

/**
 * Holds if a value flows from `source` to `sink` in zero or more local
 * (intra-procedural) value-preserving steps.
 */
pragma[inline]
predicate localFlow(Node source, Node sink) { localFlowStep*(source, sink) }

/**
 * Holds if a value can flow from `e1` to `e2` in zero or more
 * local (intra-procedural) value-preserving steps.
 */
pragma[inline]
predicate localExprFlow(CfgNodes::ExprCfgNode e1, CfgNodes::ExprCfgNode e2) {
  localFlow(exprNode(e1), exprNode(e2))
}

/** A reference contained in an object. */
class Content extends TContent {
  /** Gets a textual representation of this content. */
  string toString() {
    exists(string name | this = TFieldContent(name) and result = "Field[" + name + "]")
    or
    this = TElementContent() and result = "Element"
  }

  /** Gets the location of this content. */
  Location getLocation() { none() }
}

/** A named object field recorded by the extractor. */
class FieldContent extends Content, TFieldContent {
  /** Gets the extracted field name. */
  string getName() { this = TFieldContent(result) }
}

/** An array / subscript element recorded by the extractor. */
class ElementContent extends Content, TElementContent { }

/** Provides different sub classes of `Content`. */
module Content { }

/**
 * An entity that represents a set of `Content`s.
 *
 * The set may be interpreted differently depending on whether it is
 * stored into (`getAStoreContent`) or read from (`getAReadContent`).
 */
class ContentSet extends TContentSet {
  /** Holds if this content set is the singleton `{c}`. */
  predicate isSingleton(Content c) { this = TSingletonContent(c) }

  /** Gets a textual representation of this content set. */
  string toString() {
    exists(Content c |
      this.isSingleton(c) and
      result = c.toString()
    )
  }

  /** Gets a content that may be stored into when storing into this set. */
  Content getAStoreContent() { this.isSingleton(result) }

  /** Gets a content that may be read from when reading from this set. */
  Content getAReadContent() { this.isSingleton(result) }
}

/**
 * Holds if the guard `g` validates the expression `e` upon evaluating to `branch`.
 *
 * The expression `e` is expected to be a syntactic part of the guard `g`.
 * For example, the guard `g` might be a call `isSafe(x)` and the expression `e`
 * the argument `x`.
 */
signature predicate guardChecksSig(CfgNodes::AstCfgNode g, CfgNode e, boolean branch);

/**
 * Provides a set of barrier nodes for a guard that validates an expression.
 *
 * This is expected to be used in `isBarrier`/`isSanitizer` definitions
 * in data flow and taint tracking.
 */
module BarrierGuard<guardChecksSig/3 guardChecks> {
  /** Gets a node that is safely guarded by the given guard check. */
  Node getABarrierNode() {
    none() // TODO
  }
}
