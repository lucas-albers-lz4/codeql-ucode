/** Partial markup ordering for default imports and function creation. */

import codeql.ucode.Markup
import codeql.ucode.Diagnostics

module MarkupCreationCFG {
  private predicate clean(UcodeMarkup::Markup root) {
    exists(root.getLocation().getFile().getRelativePath()) and
    not exists(Diagnostic d | d.getLocation().getFile() = root.getLocation().getFile()) and
    not exists(UcodeMarkup::AstNode c |
      c.getLocation().getFile() = root.getLocation().getFile() and
      (
        c instanceof UcodeMarkup::Comment or
        c instanceof UcodeMarkup::DocComment or
        c instanceof UcodeMarkup::HashBangLine
      )
    )
  }

  private predicate supportedChild(UcodeMarkup::AstNode n) {
    exists(UcodeMarkup::AstNode p | p = n.getParent() |
      p instanceof UcodeMarkup::Markup and
      (
        n instanceof UcodeMarkup::StatementTagOpen or
        n instanceof UcodeMarkup::ImportStatement or
        n instanceof UcodeMarkup::ExpressionStatement
      )
      or
      exists(UcodeMarkup::ImportStatement i | p = i |
        n = i.getClause()
        or
        n = i.getSource()
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = ["import", "from", ";"]
      )
      or
      exists(UcodeMarkup::ImportClause c | p = c | n = c.getDefault())
      or
      p instanceof UcodeMarkup::String and
      (
        n instanceof UcodeMarkup::StringFragment
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = ["'", "\""]
      )
      or
      exists(UcodeMarkup::ExpressionStatement s | p = s |
        n = s.getChild()
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = ";"
      )
      or
      exists(UcodeMarkup::AssignmentExpression a | p = a |
        n = a.getLeft()
        or
        n = a.getRight()
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = "="
      )
      or
      exists(UcodeMarkup::MemberExpression m | p = m |
        n = m.getObject()
        or
        n = m.getProperty()
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = "."
      )
      or
      exists(UcodeMarkup::FunctionExpression f | p = f |
        n = f.getParameters()
        or
        n = f.getBody()
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = "function"
      )
      or
      p instanceof UcodeMarkup::FormalParameters and
      (
        n instanceof UcodeMarkup::Identifier
        or
        n instanceof UcodeMarkup::ReservedWord and n.toString() = ["(", ")", ","]
      )
    )
  }

  private predicate inBody(UcodeMarkup::AstNode n, UcodeMarkup::Markup root) {
    exists(UcodeMarkup::FunctionExpression f |
      f.getParent+() = root and n.getParent*() = f.getBody()
    )
  }

  /** Whether all top-level syntax belongs to this partial ordering contract. */
  predicate hasTopLevelObservation(UcodeMarkup::Markup root) {
    clean(root) and
    not exists(UcodeMarkup::AstNode n |
      n.getParent+() = root and not inBody(n, root) and not supportedChild(n)
    ) and
    not exists(UcodeMarkup::ImportStatement i | i.getParent() = root |
      not exists(i.getClause().getDefault()) or
      exists(i.getClause().getNamed()) or
      exists(i.getClause().getNamespace()) or
      not exists(i.getSource())
    ) and
    not exists(UcodeMarkup::ExpressionStatement s | s.getParent() = root |
      not exists(
        UcodeMarkup::AssignmentExpression a, UcodeMarkup::MemberExpression m,
        UcodeMarkup::FunctionExpression f
      |
        s.getChild() = a and
        a.getLeft() = m and
        a.getRight() = f and
        m.getObject() instanceof UcodeMarkup::Identifier and
        exists(m.getProperty()) and
        not exists(m.getOptionalChain()) and
        exists(f.getParameters()) and
        exists(f.getBody()) and
        not exists(f.getName())
      )
    )
  }

  /** A callable scope is identified by the exact function expression. */
  class CallableScope extends UcodeMarkup::FunctionExpression {
    CallableScope() {
      exists(
        UcodeMarkup::Markup root, UcodeMarkup::ExpressionStatement s,
        UcodeMarkup::AssignmentExpression a
      |
        hasTopLevelObservation(root) and
        s.getParent() = root and
        s.getChild() = a and
        a.getRight() = this
      )
    }
  }

  private predicate bodyAllowed(UcodeMarkup::AstNode n, CallableScope f) {
    n.getParent() = f.getBody() and
    (
      n instanceof UcodeMarkup::LexicalDeclaration
      or n instanceof UcodeMarkup::ExpressionStatement
      or
      n instanceof UcodeMarkup::ReservedWord and n.toString() = ["{", "}"]
    )
    or
    exists(UcodeMarkup::ExpressionStatement s | n.getParent() = s and s.getParent() = f.getBody() |
      n = s.getChild() or n instanceof UcodeMarkup::ReservedWord and n.toString() = ";"
    )
    or
    exists(UcodeMarkup::LexicalDeclaration d | n.getParent() = d and d.getParent() = f.getBody() |
      n = d.getChild(_) or n instanceof UcodeMarkup::ReservedWord
    )
    or
    exists(UcodeMarkup::VariableDeclarator v |
      n.getParent() = v and v.getParent().getParent() = f.getBody()
    |
      n = v.getName()
      or
      n = v.getValue()
      or
      n instanceof UcodeMarkup::ReservedWord and n.toString() = "="
    )
  }

  // Restrict calls to non-optional identifier or simple dotted references, and
  // arguments to the same shapes. This is a source-order observation only.
  private predicate simpleRef(UcodeMarkup::AstNode n) {
    n instanceof UcodeMarkup::Identifier or
    exists(UcodeMarkup::MemberExpression m | n = m |
      m.getObject() instanceof UcodeMarkup::Identifier and
      exists(m.getProperty()) and not exists(m.getOptionalChain())
    )
  }

  private predicate callChild(UcodeMarkup::AstNode n, CallableScope f) {
    exists(UcodeMarkup::CallExpression c | c.getParent+() = f.getBody() |
      n.getParent() = c and (n = c.getFunction() or n = c.getArguments())
      or
      n.getParent() = c.getArguments() and
        (simpleRef(n) or n instanceof UcodeMarkup::ReservedWord and n.toString() = ["(", ")", ","])
      or
      exists(UcodeMarkup::MemberExpression m | m.getParent*() = c |
        n.getParent() = m and
        (n = m.getObject() or n = m.getProperty() or
         n instanceof UcodeMarkup::ReservedWord and n.toString() = ".")
      )
    )
  }

  /** Whether this callable's body has a complete graph in this bounded contract. */
  predicate isCallableCovered(CallableScope f) {
    not exists(UcodeMarkup::AstNode n | n.getParent+() = f.getBody() and not bodyAllowed(n, f) and not callChild(n, f)) and
    not exists(UcodeMarkup::LexicalDeclaration d | d.getParent() = f.getBody() |
      count(UcodeMarkup::VariableDeclarator v | v.getParent() = d) != 1
      or
      not exists(UcodeMarkup::VariableDeclarator v | v.getParent() = d |
        exists(v.getName()) and
        (v.getValue() instanceof UcodeMarkup::Number or v.getValue() instanceof UcodeMarkup::CallExpression)
      )
    ) and
    not exists(UcodeMarkup::ExpressionStatement s | s.getParent() = f.getBody() |
      not s.getChild() instanceof UcodeMarkup::CallExpression
    ) and
    not exists(UcodeMarkup::CallExpression c | c.getParent+() = f.getBody() |
      not simpleRef(c.getFunction()) or not exists(c.getArguments()) or exists(c.getOptionalChain()) or
      not (c.getParent() instanceof UcodeMarkup::VariableDeclarator or
           c.getParent() instanceof UcodeMarkup::ExpressionStatement)
    )
  }

  private predicate topAst(UcodeMarkup::AstNode n, UcodeMarkup::Markup root) {
    hasTopLevelObservation(root) and
    n.getParent+() = root and
    not inBody(n, root) and
    (
      n instanceof UcodeMarkup::ImportStatement
      or
      n instanceof UcodeMarkup::ExpressionStatement
      or
      n instanceof UcodeMarkup::AssignmentExpression
      or
      n instanceof UcodeMarkup::MemberExpression
      or
      n instanceof UcodeMarkup::FunctionExpression
      or
      n instanceof UcodeMarkup::Identifier and
      n.getParent() instanceof UcodeMarkup::MemberExpression
    )
  }

  private predicate callableAst(UcodeMarkup::AstNode n, CallableScope f) {
    isCallableCovered(f) and
    n.getParent+() = f.getBody() and
    (n instanceof UcodeMarkup::LexicalDeclaration or n instanceof UcodeMarkup::Number or
     n instanceof UcodeMarkup::ExpressionStatement or n instanceof UcodeMarkup::CallExpression or
     n instanceof UcodeMarkup::MemberExpression or
     n instanceof UcodeMarkup::Identifier and
       (n.getParent() instanceof UcodeMarkup::CallExpression or
        n.getParent() instanceof UcodeMarkup::Arguments or
        n.getParent() instanceof UcodeMarkup::MemberExpression))
  }

  private newtype TNode =
    TTop(UcodeMarkup::AstNode n, UcodeMarkup::Markup root) { topAst(n, root) } or
    TBody(UcodeMarkup::AstNode n, CallableScope f) { callableAst(n, f) } or
    TEntry(CallableScope f) { isCallableCovered(f) } or
    TExit(CallableScope f) { isCallableCovered(f) }

  /** A node belongs to either the top-level fragment or a separate callable. */
  class Node extends TNode {
    string toString() { result = this.getRole() }

    UcodeMarkup::Markup getTopScope() { this = TTop(_, result) }

    CallableScope getCallableScope() {
      this = TBody(_, result) or this = TEntry(result) or this = TExit(result)
    }

    UcodeMarkup::AstNode getAstNode() { this = TTop(result, _) or this = TBody(result, _) }

    string getRole() {
      this = TEntry(_) and result = "entry"
      or
      this = TExit(_) and result = "exit"
      or
      this.getAstNode() instanceof UcodeMarkup::ImportStatement and result = "import-completion"
      or
      this.getAstNode() instanceof UcodeMarkup::Identifier and exists(this.getTopScope()) and
      result = "object-identifier"
      or
      this.getAstNode() instanceof UcodeMarkup::Identifier and exists(this.getCallableScope()) and
      result = "identifier"
      or
      this.getAstNode() instanceof UcodeMarkup::MemberExpression and result = "member-reference"
      or
      this.getAstNode() instanceof UcodeMarkup::FunctionExpression and result = "function-creation"
      or
      this.getAstNode() instanceof UcodeMarkup::AssignmentExpression and
      result = "assignment-completion"
      or
      this.getAstNode() instanceof UcodeMarkup::ExpressionStatement and
      result = "statement-completion"
      or
      this.getAstNode() instanceof UcodeMarkup::CallExpression and result = "call-completion"
      or
      this.getAstNode() instanceof UcodeMarkup::Number and result = "initializer"
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
    (a.getTopScope() = b.getTopScope() or a.getCallableScope() = b.getCallableScope()) and
    (
      a.getRole() = "entry" and b.getRole() != "entry"
      or
      b.getRole() = "exit" and a.getRole() != "exit"
      or
      beforeAst(a.getAstNode(), b.getAstNode())
    )
  }

  /** An immediate normal edge, never crossing scope boundaries. */
  predicate edge(Node a, Node b) {
    before(a, b) and
    not exists(Node c | before(a, c) and before(c, b))
  }
}
