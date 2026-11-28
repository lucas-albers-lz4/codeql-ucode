/** Test-only syntax association; this is not data flow or runtime binding. */

import codeql.ucode.Markup
import codeql.ucode.Diagnostics

module LocalAssociation {
  // Unbraced if/else and while bodies can bind in the enclosing scope.
  // Block, alternate-syntax and other nested scopes are not traversed.
  private predicate rootStatement(UcodeMarkup::Markup root, UcodeMarkup::AstNode node) {
    node.getParent() = root
    or
    exists(UcodeMarkup::IfStatement parent |
      rootStatement(root, parent) and
      (node = parent.getConsequence() or node = parent.getAlternative().getChild())
    )
    or
    exists(UcodeMarkup::WhileStatement parent |
      rootStatement(root, parent) and node = parent.getBody()
    )
  }

  private predicate rootDeclaration(UcodeMarkup::Markup root, UcodeMarkup::AstNode declaration) {
    rootStatement(root, declaration)
    or
    exists(UcodeMarkup::ExportStatement e |
      rootStatement(root, e) and declaration = e.getDeclaration()
    )
  }

  private predicate importedName(UcodeMarkup::ImportStatement i, string name) {
    name = i.getClause().getDefault().toString()
    or
    name = i.getClause().getNamespace().getChild().toString()
    or
    exists(UcodeMarkup::ImportSpecifier s | s = i.getClause().getNamed().getChild(_) |
      name = s.getAlias().toString()
      or
      not exists(s.getAlias()) and name = s.getName().toString()
    )
  }

  private predicate possibleRootCompetitor(
    UcodeMarkup::Markup root, UcodeMarkup::VariableDeclarator chosen, string name
  ) {
    exists(UcodeMarkup::LexicalDeclaration d, UcodeMarkup::VariableDeclarator v |
      rootDeclaration(root, d) and
      v = d.getChild(_) and
      v != chosen and
      v.getName().toString() = name
    )
    or
    exists(UcodeMarkup::FunctionDeclaration f |
      rootDeclaration(root, f) and f.getName().toString() = name
    )
    or
    exists(UcodeMarkup::ImportStatement i | i.getParent() = root and importedName(i, name))
  }

  private predicate precedes(UcodeMarkup::ExpressionTag before, UcodeMarkup::ExpressionTag selected) {
    before.getParent() = selected.getParent() and
    before.getParentIndex() < selected.getParentIndex()
  }

  private predicate unsafePrefix(UcodeMarkup::ExpressionTag selected, string name) {
    name = selected.getChild().toString() and
    (
      exists(
        UcodeMarkup::ExpressionTag before, UcodeMarkup::AstNode write, UcodeMarkup::AstNode target
      |
        precedes(before, selected) and
        write.getParent+() = before and
        (
          write instanceof UcodeMarkup::AssignmentExpression and
          target = write.(UcodeMarkup::AssignmentExpression).getLeft()
          or
          write instanceof UcodeMarkup::AugmentedAssignmentExpression and
          target = write.(UcodeMarkup::AugmentedAssignmentExpression).getLeft()
          or
          write instanceof UcodeMarkup::UpdateExpression and
          target = write.(UcodeMarkup::UpdateExpression).getArgument()
        ) and
        (not target instanceof UcodeMarkup::Identifier or target.toString() = name)
      )
      or
      // Binding-producing expressions and unsupported delete operations are unresolved.
      exists(UcodeMarkup::ExpressionTag before, UcodeMarkup::AstNode n |
        precedes(before, selected) and
        n.getParent+() = before and
        (
          n instanceof UcodeMarkup::FunctionExpression or
          n instanceof UcodeMarkup::ArrowFunction or
          n instanceof UcodeMarkup::DeleteExpression
        )
      )
    )
  }

  predicate associates(
    UcodeMarkup::Markup root, UcodeMarkup::LexicalDeclaration declaration,
    UcodeMarkup::VariableDeclarator declarator, UcodeMarkup::TextStatement text,
    UcodeMarkup::ExpressionTag tag, UcodeMarkup::Identifier read
  ) {
    exists(root.getLocation().getFile().getRelativePath()) and
    declaration.getParent() = root and
    declaration.getKind().toString() = "const" and
    declarator = declaration.getChild(_) and
    count(UcodeMarkup::VariableDeclarator d | d = declaration.getChild(_)) = 1 and
    exists(declarator.getName()) and
    exists(declarator.getValue()) and
    text.getParent() = root and
    text.getParentIndex() = declaration.getParentIndex() + 1 and
    tag.getParent() = text and
    read = tag.getChild() and
    count(UcodeMarkup::AstNode c | c.getParent() = tag) = 3 and
    read.toString() = declarator.getName().toString() and
    not possibleRootCompetitor(root, declarator, read.toString()) and
    not unsafePrefix(tag, read.toString()) and
    not exists(Diagnostic d | d.getLocation().getFile() = root.getLocation().getFile())
  }
}
