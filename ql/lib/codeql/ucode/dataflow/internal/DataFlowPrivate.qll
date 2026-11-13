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

private class ReturnValueNodeImpl extends ReturnValueNode, ReturnNode, NodeImpl {
  override CfgScope getCfgScope() { result = this.getCfgNode().getScope() }

  override Location getLocationImpl() { result = this.getCfgNode().getLocation() }

  override string toStringImpl() { result = "return value" }

  override ReturnKind getKind() { result = TNormalReturnKind() }
}

/**
 * Object / array literal CFG node. Those wrappers are not `TExpr`, so they
 * have no `ExprCfgNode`. Used as `storeStep` targets (and nested stores).
 */
private class ContentContainerNodeImpl extends ContentContainerNode, NodeImpl {
  override CfgScope getCfgScope() { result = this.getCfgNode().getScope() }

  override Location getLocationImpl() { result = this.getCfgNode().getLocation() }

  override string toStringImpl() { result = this.getCfgNode().toString() }
}

/**
 * SSA value flow with per-definition identities.
 *
 * Ordered CFG nodes distinguish expression evaluation, reads and writes.
 * Definitions flow to their reads through phi joins; expression values flow
 * through assignments, value-preserving choices and returns. Not call
 * resolution (`viableSourceCallable` stays
 * `none()`) and not imported luci.sys `path_found`.
 */
module SsaFlow {
  /**
   * Innermost CFG node containing `inner`, excluding nested CFG nodes.
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
    exists(UCODE::TernaryExpression t |
      e = t and
      (result = copyValue(t.getConsequence()) or result = copyValue(t.getAlternative()))
    )
    or
    exists(UCODE::BinaryExpression b |
      e = b and
      b.getOperator() in ["&&", "||", "??"] and
      (result = copyValue(b.getLeft()) or result = copyValue(b.getRight()))
    )
    or
    exists(UCODE::AugmentedAssignmentExpression a |
      e = a and
      a.getOperator() in ["&&=", "||=", "??="] and
      (result = copyValue(a.getLeft()) or result = copyValue(a.getRight()))
    )
    or
    not e instanceof UCODE::ParenthesizedExpression and
    not e instanceof UCODE::SequenceExpression and
    not e instanceof UCODE::AssignmentExpression and
    not e instanceof UCODE::TernaryExpression and
    not exists(UCODE::BinaryExpression b | e = b and b.getOperator() in ["&&", "||", "??"]) and
    not exists(UCODE::AugmentedAssignmentExpression a |
      e = a and a.getOperator() in ["&&=", "||=", "??="]
    ) and
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
    exists(VariableWriteAccess wa, UCODE::AssignmentExpression a |
      wa.getVariable() = dstDef.getSourceVariable() and
      astInCfg(dstDef.getControlFlowNode(), wa.getAstNode()) and
      a = wa.getWriteOperation() and
      result = wa.getAssignedRhs()
    )
    or
    exists(VariableWriteAccess wa, UCODE::AugmentedAssignmentExpression a |
      wa.getVariable() = dstDef.getSourceVariable() and
      a = wa.getWriteOperation() and
      a.getOperator() in ["&&=", "||=", "??="] and
      toTreeSitter(dstDef.getControlFlowNode().getAstNode()) = a and
      result = wa.getAssignedRhs()
    )
  }

  /** Write of `def` to a read reachable through any phi joins. */
  predicate ssaDefToRead(Node nodeFrom, Node nodeTo) {
    exists(Ssa::WriteDefinition def, CfgNode read |
      nodeFrom = TSsaDefNode(def) and
      read = def.getAFlowRead() and
      nodeTo = TSsaReadNode(def, read)
    )
  }

  /**
   * Identifier copy: the assigned value of `dstDef` is a read of `srcDef`.
   * Does not step through calls, field reads, or independent declarators.
   */
  predicate identifierCopy(Node nodeFrom, Node nodeTo) {
    exists(
      Ssa::WriteDefinition srcDef, Ssa::WriteDefinition dstDef, CfgNode read, VariableReadAccess ra,
      UCODE::Identifier ident
    |
      nodeFrom = TSsaReadNode(srcDef, read) and
      nodeTo = TSsaDefNode(dstDef) and
      read.getScope() = dstDef.getControlFlowNode().getScope() and
      srcDef.getSourceVariable() != dstDef.getSourceVariable() and
      ra.getVariable() = srcDef.getSourceVariable() and
      read.getAstNode() = ra.getAstNode() and
      toTreeSitter(ra.getAstNode()) = ident and
      copyValue(assignedRhs(dstDef)) = ident
    )
  }

  /** A precise SSA read denotes the value of its identifier expression. */
  predicate readToExpression(Node nodeFrom, Node nodeTo) {
    exists(Ssa::WriteDefinition def, CfgNode read, CfgNodes::ExprCfgNode expr |
      nodeFrom = TSsaReadNode(def, read) and nodeTo = TExprNode(expr) and expr = read
    )
  }

  /** An expression value assigned to a local reaches that particular write. */
  predicate expressionToDefinition(Node nodeFrom, Node nodeTo) {
    exists(CfgNodes::ExprCfgNode expr, Ssa::WriteDefinition def |
      nodeFrom = TExprNode(expr) and
      nodeTo = TSsaDefNode(def) and
      expr.getScope() = def.getControlFlowNode().getScope() and
      copyValue(assignedRhs(def)) = toTreeSitter(expr.getAstNode())
    )
  }

  /** A literal container assigned to a local reaches that particular write. */
  predicate containerToDefinition(Node nodeFrom, Node nodeTo) {
    exists(CfgNodes::AstCfgNode container, Ssa::WriteDefinition def, UCODE::AstNode raw |
      container = containerCfg(raw) and
      nodeFrom = TContentContainerNode(container) and
      nodeTo = TSsaDefNode(def) and
      container.getScope() = def.getControlFlowNode().getScope() and
      copyValue(assignedRhs(def)) = raw
    )
  }

  /** Expressions preserve values through parentheses, final comma operands and choices. */
  predicate expressionValue(Node nodeFrom, Node nodeTo) {
    exists(CfgNodes::ExprCfgNode fromExpr, CfgNodes::ExprCfgNode toExpr |
      nodeFrom = TExprNode(fromExpr) and
      nodeTo = TExprNode(toExpr) and
      fromExpr.getScope() = toExpr.getScope() and
      toTreeSitter(fromExpr.getAstNode()) != toTreeSitter(toExpr.getAstNode()) and
      copyValue(toTreeSitter(toExpr.getAstNode())) = toTreeSitter(fromExpr.getAstNode())
    )
  }

  /** A literal container can be the value of a surrounding expression. */
  predicate containerToExpression(Node nodeFrom, Node nodeTo) {
    exists(CfgNodes::AstCfgNode container, CfgNodes::ExprCfgNode expr, UCODE::AstNode raw |
      container = containerCfg(raw) and
      nodeFrom = TContentContainerNode(container) and
      nodeTo = TExprNode(expr) and
      container.getScope() = expr.getScope() and
      copyValue(toTreeSitter(expr.getAstNode())) = raw
    )
  }

  /** The value of the returned expression reaches its callable's return node. */
  predicate expressionToReturn(Node nodeFrom, Node nodeTo) {
    exists(CfgNodes::ExprCfgNode expr, CfgNodes::AstCfgNode retNode, UCODE::ReturnStatement ret |
      nodeFrom = TExprNode(expr) and
      nodeTo = TReturnNode(retNode) and
      retNode.getAstNode() = TReturnStatement(ret) and
      expr.getScope() = retNode.getScope() and
      copyValue(ret.getChild()) = toTreeSitter(expr.getAstNode())
    )
  }

  /** A returned object or array literal reaches the callable's return node. */
  predicate containerToReturn(Node nodeFrom, Node nodeTo) {
    exists(
      CfgNodes::AstCfgNode container, CfgNodes::AstCfgNode retNode, UCODE::AstNode raw,
      UCODE::ReturnStatement ret
    |
      container = containerCfg(raw) and
      nodeFrom = TContentContainerNode(container) and
      nodeTo = TReturnNode(retNode) and
      retNode.getAstNode() = TReturnStatement(ret) and
      container.getScope() = retNode.getScope() and
      copyValue(ret.getChild()) = raw
    )
  }

  predicate localFlowStep(Node nodeFrom, Node nodeTo) {
    ssaDefToRead(nodeFrom, nodeTo)
    or
    identifierCopy(nodeFrom, nodeTo)
    or
    readToExpression(nodeFrom, nodeTo)
    or
    expressionToDefinition(nodeFrom, nodeTo)
    or
    containerToDefinition(nodeFrom, nodeTo)
    or
    expressionValue(nodeFrom, nodeTo)
    or
    containerToExpression(nodeFrom, nodeTo)
    or
    expressionToReturn(nodeFrom, nodeTo)
    or
    containerToReturn(nodeFrom, nodeTo)
  }
}

/** Provides predicates related to local data flow. */
module LocalFlow {
  pragma[nomagic]
  predicate localFlowStepCommon(Node nodeFrom, Node nodeTo) { none() }

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

/**
 * Static field names the extractor already records. Not computed
 * property names. Not production taint.
 */
private string extractedFieldName() {
  (
    exists(UCODE::MemberExpression m | result = m.getProperty().getValue())
    or
    exists(UCODE::Pair p | result = staticPairKey(p))
    or
    exists(UCODE::ShorthandPropertyIdentifier s | result = s.getValue())
    or
    exists(UCODE::SubscriptExpression s, UCODE::String key |
      key = s.getIndex() and result = staticStringKey(key)
    )
  )
}

/** String keys without escape sequences, whose fragments are their actual value. */
private string staticStringKey(UCODE::String s) {
  not exists(UCODE::EscapeSequence escape | escape = s.getChild(_)) and
  (
    result =
      strictconcat(int i, UCODE::StringFragment frag |
        frag = s.getChild(i)
      |
        frag.getValue() order by i
      )
    or
    not exists(s.getChild(_)) and result = ""
  )
}

/** Property-identifier or unescaped string pair keys. Not computed names. */
private string staticPairKey(UCODE::Pair p) {
  result = p.getKey().(UCODE::PropertyIdentifier).getValue()
  or
  exists(UCODE::String s | s = p.getKey() and result = staticStringKey(s))
}

/**
 * Object of `obj.field = v` or `arr[i] = v`. Compound assignment and
 * deletion are not stores of the RHS. Bases without a canonical
 * `ExprCfgNode` (object/array literals, `this`) do not inhabit
 * `TExprPostUpdateNode`.
 */
private UCODE::Expression assignmentStoreBase(UCODE::AssignmentExpression a) {
  result = a.getLeft().(UCODE::MemberExpression).getObject()
  or
  result = a.getLeft().(UCODE::SubscriptExpression).getObject()
}

/** Subscript reads or non-empty array literals. */
private predicate extractedElementContent() {
  exists(UCODE::SubscriptExpression s)
  or
  exists(UCODE::Array a, int i | exists(a.getChild(i)))
}

/**
 * Wrapper whose generated class matches the TreeSitter node. Drops the
 * `TExpression` / `TPrimaryExpression` aliases for the same entity.
 */
private predicate canonicalWrapper(AstNode n, UCODE::AstNode raw) {
  toTreeSitter(n) = raw and
  n.getAPrimaryQlClass() = raw.getAPrimaryQlClass()
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
    TSsaReadNode(Ssa::WriteDefinition def, CfgNode read) { read = def.getAFlowRead() } or
    TReturnNode(CfgNodes::AstCfgNode n) { n.getAstNode() instanceof ReturnStatement } or
    TExprPostUpdateNode(CfgNodes::ExprCfgNode n) {
      canonicalWrapper(n.getExpr(), assignmentStoreBase(_))
    } or
    TContentContainerNode(CfgNodes::AstCfgNode n) {
      n.getAstNode() instanceof Object or n.getAstNode() instanceof Array
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

  /**
   * Field and element content from extracted AST.
   *
   * `Field` names are member properties, object pair keys, and shorthand
   * properties. `Element` holds when a subscript or a non-empty array is
   * present. No `Future`: ucode has no async/future nodes. `storeStep` /
   * `readStep` are inhabited from member, subscript, object, array, and
   * assignment AST; they are not wired into `localFlowStep`. Not call
   * resolution and not `path_found`.
   */
  cached
  newtype TContent =
    TFieldContent(string name) { name = extractedFieldName() } or
    TElementContent() { extractedElementContent() }

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
 * CFG expression whose wrapper class matches the TreeSitter node.
 */
private CfgNodes::ExprCfgNode exprCfg(UCODE::AstNode raw) {
  canonicalWrapper(result.getExpr(), raw)
}

/**
 * Object / array CFG node whose wrapper class matches the TreeSitter node.
 */
private CfgNodes::AstCfgNode containerCfg(UCODE::AstNode raw) {
  canonicalWrapper(result.getAstNode(), raw) and
  (
    result.getAstNode() instanceof Object or
    result.getAstNode() instanceof Array
  )
}

/**
 * Value of an extracted AST node: expression CFG when the wrapper is
 * `TExpr`, otherwise the object/array container. Numbers, arrows,
 * templates, `this`, regex, and spreads have neither.
 */
private Node valueNode(UCODE::AstNode raw) {
  result = TExprNode(exprCfg(raw))
  or
  result = TContentContainerNode(containerCfg(raw))
}

/**
 * Holds if data can flow from `node1` to `node2` via an assignment to
 * content `c`.
 *
 * Object pair values and shorthand properties store `Field[name]`.
 * Array children store `Element`. Assignment `obj.field = v` /
 * `arr[i] = v` stores into `TExprPostUpdateNode` of the extracted
 * base expression. Not summary steps and not `localFlowStep`.
 */
predicate storeStep(Node node1, ContentSet c, Node node2) {
  exists(UCODE::Object obj, UCODE::Pair p, string name |
    p = obj.getChild(_) and
    name = staticPairKey(p) and
    node1 = valueNode(p.getValue()) and
    node2 = TContentContainerNode(containerCfg(obj)) and
    c.isSingleton(TFieldContent(name))
  )
  or
  exists(UCODE::Object obj, UCODE::ShorthandPropertyIdentifier s |
    s = obj.getChild(_) and
    node1 = TExprNode(exprCfg(s)) and
    node2 = TContentContainerNode(containerCfg(obj)) and
    c.isSingleton(TFieldContent(s.getValue()))
  )
  or
  exists(UCODE::Array arr, int i |
    exists(arr.getChild(i)) and
    not arr.getChild(i) instanceof UCODE::SpreadElement and
    node1 = valueNode(arr.getChild(i)) and
    node2 = TContentContainerNode(containerCfg(arr)) and
    c.isSingleton(TElementContent())
  )
  or
  exists(UCODE::AssignmentExpression a, UCODE::MemberExpression m, string name |
    m = a.getLeft() and
    name = m.getProperty().getValue() and
    node1 = valueNode(a.getRight()) and
    node2 = TExprPostUpdateNode(exprCfg(m.getObject())) and
    c.isSingleton(TFieldContent(name))
  )
  or
  exists(UCODE::AssignmentExpression a, UCODE::SubscriptExpression s |
    s = a.getLeft() and
    node1 = valueNode(a.getRight()) and
    node2 = TExprPostUpdateNode(exprCfg(s.getObject())) and
    (
      c.isSingleton(TElementContent())
      or
      exists(UCODE::String key, string name |
        key = s.getIndex() and name = staticStringKey(key) and c.isSingleton(TFieldContent(name))
      )
      or
      not exists(UCODE::String key | key = s.getIndex() and exists(staticStringKey(key))) and
      exists(string name | c.isSingleton(TFieldContent(name)))
    )
  )
}

/** Plain assignment and deletion evaluate a reference without reading its value. */
private predicate writeOnlyReference(UCODE::AstNode n) {
  exists(UCODE::AssignmentExpression a | a.getLeft() = n)
  or
  exists(UCODE::DeleteExpression d | d.getArgument() = n)
}

/**
 * Holds if there is a read step of content `c` from `node1` to `node2`.
 *
 * `obj.field` reads `Field[field]`. `obj[i]` reads `Element` and any
 * object fields that the index may name. No
 * `Future` (no async AST). Not summary steps and not `localFlowStep`.
 */
predicate readStep(Node node1, ContentSet c, Node node2) {
  exists(UCODE::MemberExpression m, string name |
    name = m.getProperty().getValue() and
    not writeOnlyReference(m) and
    node1 = valueNode(m.getObject()) and
    node2 = TExprNode(exprCfg(m)) and
    c.isSingleton(TFieldContent(name))
  )
  or
  exists(UCODE::SubscriptExpression s |
    not writeOnlyReference(s) and
    node1 = valueNode(s.getObject()) and
    node2 = TExprNode(exprCfg(s)) and
    (
      c.isSingleton(TElementContent())
      or
      exists(UCODE::String key, string name |
        key = s.getIndex() and name = staticStringKey(key) and c.isSingleton(TFieldContent(name))
      )
      or
      not exists(UCODE::String key | key = s.getIndex() and exists(staticStringKey(key))) and
      exists(string name | c.isSingleton(TFieldContent(name)))
    )
  )
}

/**
 * Holds if values stored inside content `c` are cleared at node `n`. For example,
 * any value stored inside `f` is cleared at the pre-update node associated with `x`
 * in `x.f = newValue`.
 */
predicate clearsContent(Node n, ContentSet c) {
  exists(CfgNodes::ExprCfgNode e |
    n = TExprNode(e) and
    storeStep(_, c, TExprPostUpdateNode(e))
  )
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
  class ExprPostUpdateNode extends PostUpdateNodeImpl, NodeImpl, TExprPostUpdateNode {
    private CfgNodes::ExprCfgNode n;

    ExprPostUpdateNode() { this = TExprPostUpdateNode(n) }

    override Node getPreUpdateNode() { result = TExprNode(n) }

    override CfgScope getCfgScope() { result = n.getScope() }

    override Location getLocationImpl() { result = n.getLocation() }

    override string toStringImpl() { result = "[post] " + n.toString() }
  }
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
