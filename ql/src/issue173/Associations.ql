import Association

from
  UcodeMarkup::Markup root, UcodeMarkup::LexicalDeclaration declaration,
  UcodeMarkup::VariableDeclarator declarator, UcodeMarkup::TextStatement text,
  UcodeMarkup::ExpressionTag tag, UcodeMarkup::Identifier read
where LocalAssociation::associates(root, declaration, declarator, text, tag, read)
select root, declaration, declarator, declarator.getName(), declarator.getValue(), text, tag, read
