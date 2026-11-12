/**
 *  Internal implementation for Program
 *
 *  WARNING: this file is generated, do not edit manually
 */
private import AstNodes
private import TreeSitter
private import StmtSequence
private import Stmts

/**
 *  A Program AST Node.
 */
class ProgramImpl extends TProgram, StmtSequenceImpl {
  private UCODE::Program ast;

  override string getAPrimaryQlClass() { result = "Program" }

  ProgramImpl() { this = TProgram(ast) }

  override string toString() { result = ast.toString() }

  override StmtsImpl getStmts() {
    toTreeSitter(result) = ast.getChild(_)
  }

  override StmtsImpl getStmt(int index) {
    toTreeSitter(result) = ast.getChild(index)
  }
}