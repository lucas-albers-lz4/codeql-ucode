private import codeql.ucode.ast.AstNodes
private import AstNodes
private import TreeSitter
private import Stmts

/**
 *  A sequence of statements.
 */
class StmtSequenceImpl extends AstNode, TStmtSeq {
    override string getAPrimaryQlClass() { result = "StmtSequence" }
  
    abstract StmtsImpl getStmts();
  
    abstract StmtsImpl getStmt(int index);
}
  