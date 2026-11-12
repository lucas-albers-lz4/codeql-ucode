/**
 * CFG nodes wrapping AST nodes.
 *
 * Expression wrappers support local value flow. Call CFG nodes do not imply
 * an interprocedural call graph.
 */

private import codeql.ucode.AST
private import codeql.ucode.controlflow.ControlFlowGraph
private import codeql.ucode.controlflow.internal.ControlFlowGraphImpl as CfgImpl

/** A CFG node that wraps an AST node. */
class AstCfgNode extends CfgNode, CfgImpl::AstCfgNode { }

/** A CFG node that wraps an expression. */
class ExprCfgNode extends AstCfgNode {
  private Expr e;

  ExprCfgNode() { e = this.getAstNode() }

  /** Gets the underlying expression. */
  Expr getExpr() { result = e }
}

/** Statement-shaped CFG nodes used by later dataflow dispatch. */
module StmtNodes {
  /** A CFG node wrapping a call expression. */
  class CallCfgNode extends AstCfgNode {
    private CallExpression call;

    CallCfgNode() { call = this.getAstNode() }

    /** Gets the underlying call. */
    CallExpression getCall() { result = call }
  }
}
