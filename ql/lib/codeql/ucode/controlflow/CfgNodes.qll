/**
 * CFG nodes wrapping AST nodes.
 *
 * Minimal surface so `import codeql.ucode.CFG` typechecks. Stmt/expr wrappers
 * needed by SSA and dataflow are stubs; do not treat CallCfgNode as a modeled
 * interprocedural call graph.
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
