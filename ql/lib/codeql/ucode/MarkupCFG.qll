/** A bounded, separate ordering graph for clean markup roots. No data flow is modeled. */

import codeql.ucode.Markup
import codeql.ucode.Diagnostics

module MarkupCFG {
  private predicate sequence(UcodeMarkup::AstNode n) {
    n instanceof UcodeMarkup::Markup or n instanceof UcodeMarkup::TextStatement
  }

  private predicate allowedChild(UcodeMarkup::AstNode n) {
    exists(UcodeMarkup::AstNode p | p = n.getParent() |
      sequence(p) and
      (
        n instanceof UcodeMarkup::RawText
        or
        n instanceof UcodeMarkup::ExpressionTag
        or
        p instanceof UcodeMarkup::Markup and
        (
          n instanceof UcodeMarkup::LexicalDeclaration or
          n instanceof UcodeMarkup::TextStatement or
          n instanceof UcodeMarkup::StatementTagOpen
        )
        or
        p instanceof UcodeMarkup::TextStatement and
        (n instanceof UcodeMarkup::StatementTagClose or n instanceof UcodeMarkup::StatementTagOpen)
      )
      or
      exists(UcodeMarkup::ExpressionTag tag | p = tag |
        n = tag.getChild() and n instanceof UcodeMarkup::Identifier
        or
        n = tag.getOpen() and n instanceof UcodeMarkup::ExpressionTagOpen
        or
        n = tag.getClose() and n instanceof UcodeMarkup::ExpressionTagClose
      )
      or
      exists(UcodeMarkup::LexicalDeclaration decl | p = decl |
        n = decl.getChild(_) or n instanceof UcodeMarkup::ReservedWord
      )
      or
      exists(UcodeMarkup::VariableDeclarator d | p = d |
        n = d.getName()
        or
        n = d.getValue()
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = "="
      )
    )
  }

  /** Holds only for the explicitly supported, diagnostic-free root shape. */
  predicate isCovered(UcodeMarkup::Markup root) {
    exists(root.getLocation().getFile().getRelativePath()) and
    not exists(UcodeMarkup::RawText t |
      t.getParent() = root and t.getParentIndex() = 0 and t.getValue().matches("#!%")
    ) and
    not exists(Diagnostic d | d.getLocation().getFile() = root.getLocation().getFile()) and
    not exists(UcodeMarkup::AstNode n | n.getParent+() = root and not allowedChild(n)) and
    not exists(UcodeMarkup::ExpressionTag t | t.getParent+() = root |
      not t.getChild() instanceof UcodeMarkup::Identifier or
      not t.getOpen() instanceof UcodeMarkup::ExpressionTagOpen or
      not t.getClose() instanceof UcodeMarkup::ExpressionTagClose or
      count(UcodeMarkup::AstNode c | c.getParent() = t) != 3
    ) and
    not exists(UcodeMarkup::LexicalDeclaration d | d.getParent+() = root |
      count(UcodeMarkup::VariableDeclarator v | v.getParent() = d) != 1
      or
      not exists(UcodeMarkup::VariableDeclarator v | v.getParent() = d |
        exists(v.getName()) and v.getValue() instanceof UcodeMarkup::Number
      )
    )
  }

  private predicate astNode(UcodeMarkup::AstNode n, UcodeMarkup::Markup root) {
    isCovered(root) and
    n.getParent+() = root and
    (
      n instanceof UcodeMarkup::RawText
      or
      n instanceof UcodeMarkup::ExpressionTag
      or
      n instanceof UcodeMarkup::LexicalDeclaration
      or
      n instanceof UcodeMarkup::Identifier and n.getParent() instanceof UcodeMarkup::ExpressionTag
      or
      n instanceof UcodeMarkup::Number and n.getParent() instanceof UcodeMarkup::VariableDeclarator
    )
  }

  private newtype TNode =
    TAst(UcodeMarkup::AstNode n, UcodeMarkup::Markup root) { astNode(n, root) } or
    TEntry(UcodeMarkup::Markup root) { isCovered(root) } or
    TExit(UcodeMarkup::Markup root) { isCovered(root) }

  /** A node in the covered root's graph; synthetic nodes have no AST identity. */
  class Node extends TNode {
    string toString() { result = this.getRole() }

    UcodeMarkup::Markup getScope() {
      this = TAst(_, result) or this = TEntry(result) or this = TExit(result)
    }

    UcodeMarkup::AstNode getAstNode() { this = TAst(result, _) }

    string getRole() {
      this = TEntry(_) and result = "entry"
      or
      this = TExit(_) and result = "exit"
      or
      this.getAstNode() instanceof UcodeMarkup::RawText and result = "raw-text"
      or
      this.getAstNode() instanceof UcodeMarkup::Identifier and result = "identifier"
      or
      this.getAstNode() instanceof UcodeMarkup::Number and result = "initializer"
      or
      this.getAstNode() instanceof UcodeMarkup::ExpressionTag and result = "tag-completion"
      or
      this.getAstNode() instanceof UcodeMarkup::LexicalDeclaration and
      result = "declaration-completion"
    }
  }

  private predicate beforeAst(UcodeMarkup::AstNode a, UcodeMarkup::AstNode b) {
    a.getParent+() = b
    or
    exists(UcodeMarkup::AstNode x, UcodeMarkup::AstNode y |
      a.getParent*() = x and
      b.getParent*() = y and
      x.getParent() = y.getParent() and
      x.getParentIndex() < y.getParentIndex()
    )
  }

  private predicate before(Node a, Node b) {
    a.getScope() = b.getScope() and
    (
      a.getRole() = "entry" and b.getRole() != "entry"
      or
      b.getRole() = "exit" and a.getRole() != "exit"
      or
      beforeAst(a.getAstNode(), b.getAstNode())
    )
  }

  /** Holds for an immediate normal edge in a covered root. */
  predicate edge(Node a, Node b) {
    before(a, b) and
    not exists(Node c | before(a, c) and before(c, b))
  }
}
