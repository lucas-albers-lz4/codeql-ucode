/**
 * Literals in the AST.
 */

private import AstNodes
private import internal.AstNodes
private import internal.TreeSitter
private import internal.Literals

/**
 * A literal in the AST.
 */
final class Literals extends AstNode instanceof LiteralsImpl { }


/**
 * A False literal in the AST.
 */
final class False extends Literals instanceof FalseImpl {
}
/**
 * A Null literal in the AST.
 */
final class Null extends Literals instanceof NullImpl {
}
/**
 * A String literal in the AST.
 */
final class String extends Literals instanceof StringImpl {
    string getString() { result = super.getValue() }
}
/**
 * A StringFragment literal in the AST.
 */
final class StringFragment extends Literals instanceof StringFragmentImpl {
}
/**
 * A True literal in the AST.
 */
final class True extends Literals instanceof TrueImpl {
}