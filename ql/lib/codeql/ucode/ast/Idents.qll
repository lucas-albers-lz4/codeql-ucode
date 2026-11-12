
/**
 * Idents in the AST.
 */
private import AstNodes
private import Expr
// Internal imports
private import internal.AstNodes
private import internal.TreeSitter
private import internal.Idents
private import internal.Identifier
private import internal.PropertyIdentifier
private import internal.ShorthandPropertyIdentifier

/**
 * An expression in the AST.
 */
final class Idents extends IdentsImpl {
    override string getName() { result = "" }
}
/**
 * A Identifier expression in the AST.
 */
final class Identifier extends Idents instanceof IdentifierImpl { }
/**
 * A PropertyIdentifier expression in the AST.
 */
final class PropertyIdentifier extends Idents instanceof PropertyIdentifierImpl { }
/**
 * A ShorthandPropertyIdentifier expression in the AST.
 */
final class ShorthandPropertyIdentifier extends Idents instanceof ShorthandPropertyIdentifierImpl { }