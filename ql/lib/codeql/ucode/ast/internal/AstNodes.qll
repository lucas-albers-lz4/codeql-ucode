private import TreeSitter

/**
 * An AST node of a ucode program
 */
cached
newtype TAstNode =
  TArguments(UCODE::Arguments r) or
  TArray(UCODE::Array r) or
  TArrowFunction(UCODE::ArrowFunction r) or
  TAssignmentExpression(UCODE::AssignmentExpression r) or
  TAugmentedAssignmentExpression(UCODE::AugmentedAssignmentExpression r) or
  TBinaryExpression(UCODE::BinaryExpression r) or
  TBreakStatement(UCODE::BreakStatement r) or
  TCallExpression(UCODE::CallExpression r) or
  TCatchClause(UCODE::CatchClause r) or
  TComment(UCODE::Comment r) or
  TComputedPropertyName(UCODE::ComputedPropertyName r) or
  TContinueStatement(UCODE::ContinueStatement r) or
  TDeclaration(UCODE::Declaration r) or
  TDefault(UCODE::Default r) or
  TDeleteExpression(UCODE::DeleteExpression r) or
  TDocComment(UCODE::DocComment r) or
  TElifClause(UCODE::ElifClause r) or
  TElseAltClause(UCODE::ElseAltClause r) or
  TElseClause(UCODE::ElseClause r) or
  TEmptyStatement(UCODE::EmptyStatement r) or
  TEscapeSequence(UCODE::EscapeSequence r) or
  TExportClause(UCODE::ExportClause r) or
  TExportSpecifier(UCODE::ExportSpecifier r) or
  TExportStatement(UCODE::ExportStatement r) or
  TExpression(UCODE::Expression r) or
  TExpressionStatement(UCODE::ExpressionStatement r) or
  TFalse(UCODE::False r) or
  TForAltStatement(UCODE::ForAltStatement r) or
  TForInAltStatement(UCODE::ForInAltStatement r) or
  TForInStatement(UCODE::ForInStatement r) or
  TForStatement(UCODE::ForStatement r) or
  TFormalParameters(UCODE::FormalParameters r) or
  TFunctionDeclaration(UCODE::FunctionDeclaration r) or
  TFunctionExpression(UCODE::FunctionExpression r) or
  THashBangLine(UCODE::HashBangLine r) or
  TIdentifier(UCODE::Identifier r) or
  TIfAltStatement(UCODE::IfAltStatement r) or
  TIfStatement(UCODE::IfStatement r) or
  TImportClause(UCODE::ImportClause r) or
  TImportSpecifier(UCODE::ImportSpecifier r) or
  TImportStatement(UCODE::ImportStatement r) or
  TLexicalDeclaration(UCODE::LexicalDeclaration r) or
  TMemberExpression(UCODE::MemberExpression r) or
  TNamedImports(UCODE::NamedImports r) or
  TNamespaceImport(UCODE::NamespaceImport r) or
  TNull(UCODE::Null r) or
  TNumber(UCODE::Number r) or
  TObject(UCODE::Object r) or
  TOptionalChain(UCODE::OptionalChain r) or
  TPair(UCODE::Pair r) or
  TParenthesizedExpression(UCODE::ParenthesizedExpression r) or
  TPrimaryExpression(UCODE::PrimaryExpression r) or
  TProgram(UCODE::Program r) or
  TPropertyIdentifier(UCODE::PropertyIdentifier r) or
  TRegex(UCODE::Regex r) or
  TRegexFlags(UCODE::RegexFlags r) or
  TRegexPattern(UCODE::RegexPattern r) or
  TRestElement(UCODE::RestElement r) or
  TReturnStatement(UCODE::ReturnStatement r) or
  TSequenceExpression(UCODE::SequenceExpression r) or
  TShorthandPropertyIdentifier(UCODE::ShorthandPropertyIdentifier r) or
  TSpreadElement(UCODE::SpreadElement r) or
  TStatement(UCODE::Statement r) or
  TStatementBlock(UCODE::StatementBlock r) or
  TStatementList(UCODE::StatementList r) or
  TString(UCODE::String r) or
  TStringFragment(UCODE::StringFragment r) or
  TSubscriptExpression(UCODE::SubscriptExpression r) or
  TSwitchBody(UCODE::SwitchBody r) or
  TSwitchCase(UCODE::SwitchCase r) or
  TSwitchDefault(UCODE::SwitchDefault r) or
  TSwitchStatement(UCODE::SwitchStatement r) or
  TTemplateString(UCODE::TemplateString r) or
  TTemplateSubstitution(UCODE::TemplateSubstitution r) or
  TTernaryExpression(UCODE::TernaryExpression r) or
  TThis(UCODE::This r) or
  TTrue(UCODE::True r) or
  TTryStatement(UCODE::TryStatement r) or
  TUnaryExpression(UCODE::UnaryExpression r) or
  TUpdateExpression(UCODE::UpdateExpression r) or
  TVariableDeclarator(UCODE::VariableDeclarator r) or
  TWhileAltStatement(UCODE::WhileAltStatement r) or
  TWhileStatement(UCODE::WhileStatement r)

/**
 * A literal value in a ucode program
 */
class TLiterals = TFalse or TNull or TString or TStringFragment or TTrue;

/**
 *  A sequence of statements in a ucode program
 */
class TStmtSeq = TProgram or TStatementBlock;

/**
 * A statement in a ucode program
 */
class TStmts =
  TLoops or TBreakStatement or TContinueStatement or TDeclaration or TEmptyStatement or
      TExportStatement or TExpressionStatement or TForAltStatement or TForInAltStatement or
      TForInStatement or TForStatement or TFunctionDeclaration or TIfAltStatement or TIfStatement or
      TImportStatement or TLexicalDeclaration or TReturnStatement or TStatement or
      TStatementBlock or TStatementList or TSwitchStatement or TTryStatement or
      TWhileAltStatement or TWhileStatement;

/**
 * An identifier in a ucode program
 */
class TIdents = TIdentifier or TPropertyIdentifier or TShorthandPropertyIdentifier;

/**
 * A expersion value in a ucode program
 */
class TExpr =
  TStmtSeq or TIdents or TCalls or TLiterals or TConditionals or TAssignmentExpression or
      TAugmentedAssignmentExpression or TBinaryExpression or TCallExpression or TDeleteExpression or
      TExpression or TExpressionStatement or TFunctionExpression or TMemberExpression or
      TParenthesizedExpression or TPrimaryExpression or TSequenceExpression or
      TSubscriptExpression or TTernaryExpression or TUnaryExpression or TUpdateExpression;

/**
 * A expersion value in a ucode program
 */
class TConditionals =
  TDefault or TElseAltClause or TElseClause or TIfAltStatement or TIfStatement or TSwitchBody or
      TSwitchCase or TSwitchDefault or TSwitchStatement;

/**
 * A call expression in a ucode program
 */
class TCalls = TCallExpression;

/**
 * A loops in a ucode program
 */
class TLoops =
  TDocComment or TForAltStatement or TForInAltStatement or TForInStatement or TForStatement or
      TFormalParameters or TWhileAltStatement or TWhileStatement;

cached
UCODE::AstNode toTreeSitter(TAstNode n) {
  n = TArguments(result) or
  n = TArray(result) or
  n = TArrowFunction(result) or
  n = TAssignmentExpression(result) or
  n = TAugmentedAssignmentExpression(result) or
  n = TBinaryExpression(result) or
  n = TBreakStatement(result) or
  n = TCallExpression(result) or
  n = TCatchClause(result) or
  n = TComment(result) or
  n = TComputedPropertyName(result) or
  n = TContinueStatement(result) or
  n = TDeclaration(result) or
  n = TDefault(result) or
  n = TDeleteExpression(result) or
  n = TDocComment(result) or
  n = TElifClause(result) or
  n = TElseAltClause(result) or
  n = TElseClause(result) or
  n = TEmptyStatement(result) or
  n = TEscapeSequence(result) or
  n = TExportClause(result) or
  n = TExportSpecifier(result) or
  n = TExportStatement(result) or
  n = TExpression(result) or
  n = TExpressionStatement(result) or
  n = TFalse(result) or
  n = TForAltStatement(result) or
  n = TForInAltStatement(result) or
  n = TForInStatement(result) or
  n = TForStatement(result) or
  n = TFormalParameters(result) or
  n = TFunctionDeclaration(result) or
  n = TFunctionExpression(result) or
  n = THashBangLine(result) or
  n = TIdentifier(result) or
  n = TIfAltStatement(result) or
  n = TIfStatement(result) or
  n = TImportClause(result) or
  n = TImportSpecifier(result) or
  n = TImportStatement(result) or
  n = TLexicalDeclaration(result) or
  n = TMemberExpression(result) or
  n = TNamedImports(result) or
  n = TNamespaceImport(result) or
  n = TNull(result) or
  n = TNumber(result) or
  n = TObject(result) or
  n = TOptionalChain(result) or
  n = TPair(result) or
  n = TParenthesizedExpression(result) or
  n = TPrimaryExpression(result) or
  n = TProgram(result) or
  n = TPropertyIdentifier(result) or
  n = TRegex(result) or
  n = TRegexFlags(result) or
  n = TRegexPattern(result) or
  n = TRestElement(result) or
  n = TReturnStatement(result) or
  n = TSequenceExpression(result) or
  n = TShorthandPropertyIdentifier(result) or
  n = TSpreadElement(result) or
  n = TStatement(result) or
  n = TStatementBlock(result) or
  n = TStatementList(result) or
  n = TString(result) or
  n = TStringFragment(result) or
  n = TSubscriptExpression(result) or
  n = TSwitchBody(result) or
  n = TSwitchCase(result) or
  n = TSwitchDefault(result) or
  n = TSwitchStatement(result) or
  n = TTemplateString(result) or
  n = TTemplateSubstitution(result) or
  n = TTernaryExpression(result) or
  n = TThis(result) or
  n = TTrue(result) or
  n = TTryStatement(result) or
  n = TUnaryExpression(result) or
  n = TUpdateExpression(result) or
  n = TVariableDeclarator(result) or
  n = TWhileAltStatement(result) or
  n = TWhileStatement(result)
}
