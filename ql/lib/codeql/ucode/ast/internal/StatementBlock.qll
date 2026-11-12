/**
 *  Internal implementation for StatementBlock
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import StmtSequence
private import Stmts

/**
 *  A StatementBlock AST Node.
 */
class StatementBlockImpl extends TStatementBlock, StmtSequenceImpl {
  private UCODE::StatementBlock ast;

  override string getAPrimaryQlClass() { result = "StatementBlock" }

  StatementBlockImpl() { this = TStatementBlock(ast) }

  override string toString() { result = ast.toString() }

  override StmtsImpl getStmts() { result = this.getStmt(_) }

  override StmtsImpl getStmt(int index) {
    toTreeSitter(result) = ast.getChild(index) and
    not result instanceof TStatement and
    not result instanceof TDeclaration
  }
}
